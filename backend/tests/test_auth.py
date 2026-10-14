import re
from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_token, utcnow
from app.db.session import SessionLocal
from app.models import PasswordResetToken, UserSession
from app.services.mail import MailOutbox
from tests.conftest import PASSWORD


def test_login_cookie_csrf_and_logout(client, login):
    me = login()
    assert me['roles'][0]['role'] == 'STUDENT'
    assert 'password_hash' not in me
    token = client.cookies.get('campuspulse_session')
    with SessionLocal() as db:
        session = db.scalar(select(UserSession))
        assert session.token_hash == hash_token(token)
        assert session.token_hash != token
    client.headers.pop('X-CSRF-Token')
    assert client.patch('/api/v1/users/me', json={'first_name':'Changed','last_name':'Test'}).status_code == 403
    client.headers['X-CSRF-Token'] = client.cookies.get('campuspulse_csrf')
    assert client.post('/api/v1/auth/logout').status_code == 204
    assert client.get('/api/v1/auth/me').status_code == 401
    client.cookies.set('campuspulse_session', token)
    assert client.get('/api/v1/auth/me').status_code == 401


def test_invalid_login_rate_limited_and_origin_checked(client, data):
    body = {'email': 'student@example.com', 'password': 'incorrect'}
    assert client.post('/api/v1/auth/login', json=body, headers={'Origin':'https://evil.example'}).status_code == 403
    for _ in range(10):
        assert client.post('/api/v1/auth/login', json=body).status_code == 401
    limited = client.post('/api/v1/auth/login', json=body)
    assert limited.status_code == 429
    assert int(limited.headers['retry-after']) > 0


def test_forgot_password_generic_response_and_one_use_token(client, login):
    login()
    known = client.post('/api/v1/auth/forgot-password', json={'email':'student@example.com'})
    unknown = client.post('/api/v1/auth/forgot-password', json={'email':'nobody@example.com'})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    with SessionLocal() as db:
        mails = db.scalars(select(MailOutbox)).all()
        assert len(mails) == 1
        token = re.search(r'token=([A-Za-z0-9_-]+)', mails[0].text_body).group(1)
        reset = db.scalar(select(PasswordResetToken))
        assert reset.token_hash == hash_token(token)
    body = {'token':token, 'password':'New-password-2026!'}
    assert client.post('/api/v1/auth/reset-password', json=body).status_code == 200
    assert client.post('/api/v1/auth/reset-password', json=body).status_code == 400
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.post('/api/v1/auth/login', json={'email':'student@example.com','password':PASSWORD}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email':'student@example.com','password':body['password']}).status_code == 200


def test_expired_session_rejected(client, login):
    login()
    with SessionLocal() as db:
        session = db.scalar(select(UserSession))
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get('/api/v1/auth/me').status_code == 401


def test_student_cannot_invite_and_admin_cannot_escalate(client, login, data):
    body = {'email':'new@example.com','first_name':'Nouveau','last_name':'Compte','role':'STUDENT'}
    login('student')
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/users", json=body).status_code == 403
    login('admin')
    assert client.post(f"/api/v1/campuses/{data['campus_b']}/users", json=body).status_code in (403,404)
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/users", json={**body,'role':'CAMPUS_ADMIN'}).status_code == 403
    response = client.post(f"/api/v1/campuses/{data['campus_a']}/users", json=body)
    assert response.status_code == 201, response.text
    assert 'password_hash' not in response.json()
    with SessionLocal() as db:
        assert db.scalar(select(MailOutbox)).recipient == 'new@example.com'


def test_existing_account_invitation_does_not_reset_identity(client, login, data):
    login('admin')
    response = client.post(f"/api/v1/campuses/{data['campus_a']}/users", json={'email':'outsider@example.com','first_name':'Override','last_name':'Attempt'})
    assert response.status_code == 201
    assert response.json()['first_name'] == 'Outsider'
    with SessionLocal() as db:
        assert db.scalar(select(PasswordResetToken)) is None
        assert 'token=' not in db.scalar(select(MailOutbox)).text_body


def test_profile_cannot_change_role_and_password_revokes_session(client, login):
    login()
    assert client.patch('/api/v1/users/me', json={'first_name':'Student','last_name':'Test','role':'PLATFORM_ADMIN'}).status_code == 422
    response = client.patch('/api/v1/users/me/password', json={'current_password':PASSWORD,'new_password':'Changed-password-2026!'})
    assert response.status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 401


def test_public_registration_disabled(client, data, monkeypatch):
    monkeypatch.setattr(settings, 'public_registration_enabled', False)
    assert client.get('/api/v1/auth/registration-options').json() == {'enabled': False, 'campuses': []}
    assert client.post('/api/v1/auth/register', json={'email':'new@example.com','password':PASSWORD,'first_name':'A','last_name':'B','campus_id':data['campus_a']}).status_code == 403


def test_password_whitespace_is_significant(client, login):
    login()
    password = '  exact password with spaces  '
    response = client.patch('/api/v1/users/me/password', json={'current_password':PASSWORD,'new_password':password})
    assert response.status_code == 200
    assert client.post('/api/v1/auth/login', json={'email':'student@example.com','password':password.strip()}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email':'student@example.com','password':password}).status_code == 200


def test_new_recovery_link_invalidates_old_link(client, login):
    login()
    tokens = []
    for _ in range(2):
        client.post('/api/v1/auth/forgot-password', json={'email':'student@example.com'})
        with SessionLocal() as db:
            mail = db.scalar(select(MailOutbox).order_by(MailOutbox.created_at.desc()))
            tokens.append(re.search(r'token=([A-Za-z0-9_-]+)', mail.text_body).group(1))
    assert client.post('/api/v1/auth/reset-password',json={'token':tokens[0],'password':'New-password-2026!'}).status_code == 400
    assert client.post('/api/v1/auth/reset-password',json={'token':tokens[1],'password':'New-password-2026!'}).status_code == 200


def test_suspension_affects_only_selected_membership(client, login, data):
    login('admin')
    assert client.patch(f"/api/v1/campuses/{data['campus_a']}/users/{data['student']}/status",json={'status':'SUSPENDED'}).status_code == 200
    assert client.patch(f"/api/v1/campuses/{data['campus_b']}/users/{data['outsider']}/status",json={'status':'SUSPENDED'}).status_code in (403,404)
    login('student')
    assert client.get('/api/v1/auth/me').status_code == 200
    assert client.post('/api/v1/community/posts',json={'campus_id':data['campus_a'],'content':'Suspended member'}).status_code == 403
