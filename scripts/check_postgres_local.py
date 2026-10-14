"""Validate migrations and registration in a private, disposable PostgreSQL cluster.

Uses installed PostgreSQL binaries, never DATABASE_URL from the user's .env.
The cluster remains under .qa for inspection and is stopped before returning.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from threading import Barrier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=55432)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    qa = root / '.qa'
    qa.mkdir(exist_ok=True)
    # Inherit workspace ACLs: tempfile.mkdtemp restricts Windows directories to
    # the creating token, preventing PostgreSQL's restricted child from reading.
    work = qa / f'postgres-validation-{secrets.token_hex(6)}'
    work.mkdir()
    cluster = work / 'data'
    password_file = work / 'bootstrap-password'
    password = secrets.token_urlsafe(32)
    password_file.write_text(password, encoding='utf-8')
    suffix = '.exe' if os.name == 'nt' else ''
    pg_ctl = args.bin_dir / f'pg_ctl{suffix}'
    started = False
    environment = os.environ.copy()
    environment.update(
        APP_ENV='test', APP_DEBUG='false', SMTP_ENABLED='false',
        COOKIE_SECURE='false', COOKIE_DOMAIN='',
        DATABASE_URL=f'postgresql+psycopg://campuspulse_check:{password}@127.0.0.1:{args.port}/postgres',
        SECRET_KEY=secrets.token_urlsafe(48), PUBLIC_REGISTRATION_ENABLED='true',
        TRUSTED_HOSTS='["testserver","localhost","127.0.0.1"]',
        CORS_ORIGINS='["http://localhost:3000"]',
        FRONTEND_URL='http://localhost:3000', STORAGE_PATH=str(work / 'storage'),
    )

    def run(command, name):
        # PostgreSQL's Windows child can inherit pipe handles after pg_ctl exits;
        # a file avoids waiting for EOF from the long-running server process.
        log_path = work / 'last-command.log'
        with log_path.open('w', encoding='utf-8') as output:
            result = subprocess.run(command, cwd=root / 'backend', env=environment, stdout=output, stderr=subprocess.STDOUT, text=True, timeout=90)
        if result.returncode:
            # No credentials/URLs in diagnostics; output is retained only locally.
            raise RuntimeError(f'{name} failed; details in {log_path}')
        print(f'{name}: OK', flush=True)

    try:
        run([str(args.bin_dir / f'initdb{suffix}'), '-D', str(cluster), '-U', 'campuspulse_check', '--auth=scram-sha-256', '--pwfile', str(password_file), '--encoding=UTF8', '--no-locale'], 'Create isolated PostgreSQL cluster')
        run([str(pg_ctl), 'start', '-D', str(cluster), '-l', str(work / 'postgres.log'), '-w', '-o', f'-p {args.port} -h 127.0.0.1'], 'Start isolated PostgreSQL')
        started = True
        password_file.unlink()
        for arguments in (['upgrade', 'head'], ['check'], ['downgrade', 'base'], ['upgrade', 'head']):
            run([sys.executable, '-m', 'alembic', *arguments], f'Alembic {" ".join(arguments)}')
        os.environ.update(environment)
        sys.path.insert(0, str(root / 'backend'))
        from fastapi.testclient import TestClient
        from sqlalchemy import select
        from app.core.security import hash_password, utcnow
        from app.db.session import SessionLocal, engine
        from app.main import app
        from app.models import CampusMembership, RoleAssignment, StudentRegistration, User
        from app.services.mail import MailOutbox

        login_password = secrets.token_urlsafe(24)
        with SessionLocal() as db:
            admin = User(email='platform@example.com', first_name='Test', last_name='Platform', password_hash=hash_password(login_password))
            db.add(admin)
            db.flush()
            db.add(RoleAssignment(user_id=admin.id, role='PLATFORM_ADMIN'))
            db.commit()
        with TestClient(app) as client:
            result = client.post('/api/v1/auth/login', json={'email': 'platform@example.com', 'password': login_password})
            assert result.status_code == 200, f'Admin login: {result.status_code}'
            client.headers['X-CSRF-Token'] = client.cookies.get('campuspulse_csrf')
            result = client.post('/api/v1/platform/campuses', json={'name': 'Campus test PostgreSQL', 'code': 'PGCHECK', 'slug': 'postgres-check'})
            assert result.status_code == 201, f'Campus creation: {result.status_code}'
            campus_id = result.json()['id']
            assert client.post('/api/v1/auth/logout').status_code == 204
            assert client.get('/api/v1/auth/registration-options').json()['campuses'][0]['id'] == campus_id
            signup = {'email': 'student@example.com', 'first_name': 'Test', 'last_name': 'Student', 'password': login_password, 'campus_id': campus_id}
            assert client.post('/api/v1/auth/register', json={**signup, 'role': 'PLATFORM_ADMIN'}).status_code == 422
            result = client.post('/api/v1/auth/register', json=signup)
            assert result.status_code == 202, f'Pending registration: {result.status_code}'
            challenge = result.json()
            assert challenge['verification_required'] is True
            assert challenge['email'] == signup['email']
            assert not {'code', 'otp', 'password', 'password_hash'} & challenge.keys()
            with SessionLocal() as db:
                assert db.scalar(select(User).where(User.email == signup['email'])) is None
                mail = db.scalar(select(MailOutbox).where(MailOutbox.recipient == signup['email'], MailOutbox.subject == 'Votre code de vérification CampusPulse'))
                assert mail is not None, 'Verification email was not queued'
                match = re.search(r'Code : ([0-9]{6})', mail.text_body)
                assert match is not None, 'Verification email has no six-digit code'
                code = match.group(1)
            assert client.post('/api/v1/auth/login', json={'email': signup['email'], 'password': login_password}).status_code == 401
            early_resend = client.post('/api/v1/auth/resend-verification', json={'challenge_id': challenge['challenge_id']})
            assert early_resend.status_code == 429
            assert int(early_resend.headers['retry-after']) > 0
            verification = {'challenge_id': challenge['challenge_id'], 'code': code}
            wrong_code = '000000' if code != '000000' else '111111'
            assert client.post('/api/v1/auth/verify-email', json={**verification, 'code': wrong_code}).status_code == 400
            result = client.post('/api/v1/auth/verify-email', json=verification)
            assert result.status_code == 201, f'Email verification: {result.status_code}'
            assert client.post('/api/v1/auth/verify-email', json=verification).status_code == 400
            with SessionLocal() as db:
                student = db.scalar(select(User).where(User.email == signup['email']))
                assert student is not None and student.email_verified_at is not None
            assert client.post('/api/v1/auth/register', json=signup).status_code == 409
            result = client.post('/api/v1/auth/login', json={'email': signup['email'], 'password': login_password})
            assert result.status_code == 200
            assert [role['role'] for role in result.json()['roles']] == ['STUDENT']
            assert client.get('/api/v1/platform/users').status_code == 403
            client.headers['X-CSRF-Token'] = client.cookies.get('campuspulse_csrf')
            assert client.post(f'/api/v1/campuses/{campus_id}/users', json={'email': 'staff@example.com', 'first_name': 'Test', 'last_name': 'Staff', 'role': 'CAMPUS_ADMIN'}).status_code == 403
            assert client.get('/health').status_code == 200
            assert client.post('/api/v1/auth/logout').status_code == 204
        with SessionLocal() as db:
            assert len(db.scalars(select(User)).all()) == 2

        def pending_registration(email):
            """Create a fresh fixture through the public API and read its test mailbox."""
            with TestClient(app) as guest:
                result = guest.post('/api/v1/auth/register', json={**signup, 'email': email})
            assert result.status_code == 202, f'Concurrent fixture registration: {result.status_code}'
            challenge = result.json()
            with SessionLocal() as db:
                mail = db.scalar(select(MailOutbox).where(
                    MailOutbox.recipient == email,
                    MailOutbox.subject == 'Votre code de vérification CampusPulse',
                    MailOutbox.status == 'PENDING',
                ).order_by(MailOutbox.created_at.desc()))
                match = re.search(r'Code : ([0-9]{6})', mail.text_body) if mail else None
                assert match is not None, 'Concurrent fixture has no verification code'
                return challenge, match.group(1)

        def concurrent_posts(requests):
            """Two independent clients and DB sessions begin their requests together."""
            gate = Barrier(len(requests))

            def post(request):
                route, body = request
                with TestClient(app) as guest:
                    gate.wait(timeout=10)
                    return guest.post(route, json=body).status_code

            with ThreadPoolExecutor(max_workers=len(requests)) as executor:
                futures = [executor.submit(post, request) for request in requests]
                return [future.result(timeout=30) for future in futures]

        def assert_single_verified_student(email):
            with SessionLocal() as db:
                users = db.scalars(select(User).where(User.email == email)).all()
                assert len(users) == 1 and users[0].email_verified_at is not None
                user_id = users[0].id
                roles = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user_id)).all()
                assert [(role.role, role.campus_id) for role in roles] == [('STUDENT', campus_id)]
                memberships = db.scalars(select(CampusMembership).where(CampusMembership.user_id == user_id)).all()
                assert [(membership.campus_id, membership.status) for membership in memberships] == [(campus_id, 'ACTIVE')]
                assert db.scalar(select(StudentRegistration).where(StudentRegistration.email == email)) is None
                welcomes = db.scalars(select(MailOutbox).where(MailOutbox.recipient == email, MailOutbox.subject == 'Bienvenue sur CampusPulse')).all()
                assert len(welcomes) == 1, 'Concurrent verification queued duplicate welcome messages'

        # A single OTP can be consumed only once even when two workers race.
        email = 'parallel-verify@example.com'
        challenge, code = pending_registration(email)
        verify_request = ('/api/v1/auth/verify-email', {'challenge_id': challenge['challenge_id'], 'code': code})
        statuses = concurrent_posts([verify_request, verify_request])
        assert statuses.count(201) == 1 and all(status in (201, 400, 409) for status in statuses), f'Concurrent verification statuses: {statuses}'
        assert_single_verified_student(email)
        print('PostgreSQL concurrent verification creates one account, membership, role and welcome: OK', flush=True)

        # Resend and verification must serialize: either the original code wins,
        # or the resend wins and only its replacement can create the account.
        email = 'parallel-resend@example.com'
        challenge, original_code = pending_registration(email)
        with SessionLocal() as db:
            registration = db.get(StudentRegistration, challenge['challenge_id'])
            registration.resend_available_at = utcnow() - timedelta(seconds=1)
            db.commit()
        verify_status, resend_status = concurrent_posts([
            ('/api/v1/auth/verify-email', {'challenge_id': challenge['challenge_id'], 'code': original_code}),
            ('/api/v1/auth/resend-verification', {'challenge_id': challenge['challenge_id']}),
        ])
        if verify_status == 201:
            assert resend_status in (400, 409), f'Resend after concurrent verification: {resend_status}'
        else:
            assert resend_status == 200 and verify_status in (400, 409), f'Concurrent verify/resend statuses: {(verify_status, resend_status)}'
            with SessionLocal() as db:
                assert db.scalar(select(User).where(User.email == email)) is None
                registration = db.get(StudentRegistration, challenge['challenge_id'])
                mail = db.get(MailOutbox, registration.mail_id)
                match = re.search(r'Code : ([0-9]{6})', mail.text_body)
                assert match is not None
                replacement_code = match.group(1)
                assert replacement_code != original_code
            with TestClient(app) as guest:
                assert guest.post('/api/v1/auth/verify-email', json={'challenge_id': challenge['challenge_id'], 'code': original_code}).status_code == 400
                assert guest.post('/api/v1/auth/verify-email', json={'challenge_id': challenge['challenge_id'], 'code': replacement_code}).status_code == 201
        assert_single_verified_student(email)
        with SessionLocal() as db:
            assert len(db.scalars(select(User)).all()) == 4
        print('PostgreSQL concurrent resend and verification preserve single-use OTP ordering: OK', flush=True)
        engine.dispose()
        print('PostgreSQL admin, mandatory OTP, duplicate, privilege and session checks: OK', flush=True)
    finally:
        password_file.unlink(missing_ok=True)
        if started or (cluster / 'postmaster.pid').exists():
            run([str(pg_ctl), 'stop', '-D', str(cluster), '-m', 'fast', '-w'], 'Stop isolated PostgreSQL')


if __name__ == '__main__':
    main()
