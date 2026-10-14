"""Security properties of mandatory student email verification (no SMTP I/O)."""
import re
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, settings
from app.core.security import as_utc, utcnow, verify_password
from app.db.session import SessionLocal
from app.models import AuditLog, Campus, CampusMembership, PasswordResetToken, RoleAssignment, StudentRegistration, User, UserSession
from app.services import registration as registration_service
from app.services.mail import MailOutbox
from tests.conftest import PASSWORD
from tests.test_registration import registration


def begin(client, registration):
    response = client.post('/api/v1/auth/register', json=registration)
    assert response.status_code == 202, response.text
    metadata = response.json()
    with SessionLocal() as db:
        pending = db.get(StudentRegistration, metadata['challenge_id'])
        mail = db.get(MailOutbox, pending.mail_id)
        code = re.search(r'Code : ([0-9]{6})', mail.text_body).group(1)
    return metadata, code


def verify(client, pending, code):
    return client.post('/api/v1/auth/verify-email', json={'challenge_id': pending['challenge_id'], 'code': code})


def allow_resend(pending):
    with SessionLocal() as db:
        db.get(StudentRegistration, pending['challenge_id']).resend_available_at = utcnow() - timedelta(seconds=1)
        db.commit()


def latest_code(pending):
    with SessionLocal() as db:
        record = db.get(StudentRegistration, pending['challenge_id'])
        return re.search(r'Code : ([0-9]{6})', db.get(MailOutbox, record.mail_id).text_body).group(1)


def test_pending_registration_cannot_login_or_reset_and_has_no_user_authority(client, registration):
    pending, code = begin(client, registration)
    assert pending['verification_required'] is True
    assert set(pending) == {'verification_required', 'challenge_id', 'email', 'expires_at', 'resend_available_at', 'message'}
    assert code not in str(pending) and PASSWORD not in str(pending)
    assert not client.cookies.get('campuspulse_session')
    assert client.post('/api/v1/auth/login', json={'email': registration['email'], 'password': PASSWORD}).status_code == 401
    assert client.post('/api/v1/auth/forgot-password', json={'email': registration['email']}).status_code == 200
    with SessionLocal() as db:
        record = db.get(StudentRegistration, pending['challenge_id'])
        assert verify_password(PASSWORD, record.password_hash)
        assert record.code_hash != code and len(record.code_hash) == 64
        assert record.code_hash == registration_service.code_digest(record.id, code)
        assert db.scalar(select(User).where(User.email == registration['email'])) is None
        assert db.scalar(select(PasswordResetToken)) is None
        assert db.scalar(select(UserSession)) is None
        assert db.scalar(select(func.count()).select_from(CampusMembership)) == 4
        assert db.scalar(select(func.count()).select_from(RoleAssignment)) == 5
        assert db.scalar(select(AuditLog).where(AuditLog.action == 'STUDENT_REGISTERED')) is None
        mail = db.get(MailOutbox, record.mail_id)
        assert as_utc(mail.expires_at) == as_utc(record.expires_at)
        assert mail.status == 'PENDING'


def test_verification_is_single_use_purges_pending_and_creates_only_student(client, registration, data):
    pending, code = begin(client, registration)
    response = verify(client, pending, code)
    assert response.status_code == 201, response.text
    assert not client.cookies.get('campuspulse_session')
    assert verify(client, pending, code).status_code == 400
    with SessionLocal() as db:
        assert db.get(StudentRegistration, pending['challenge_id']) is None
        user = db.scalar(select(User).where(User.email == registration['email']))
        assert user.email_verified_at is not None and user.status == 'ACTIVE'
        assert [(r.role, r.campus_id) for r in db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id))] == [('STUDENT', data['campus_a'])]
        otp = db.scalar(select(MailOutbox).where(MailOutbox.subject == 'Votre code de vérification CampusPulse'))
        assert otp.status == 'CANCELLED' and code not in otp.text_body
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == 'STUDENT_REGISTERED')) == 1
        assert code not in str(db.scalar(select(AuditLog).where(AuditLog.action == 'STUDENT_REGISTERED')).details)


def test_wrong_attempts_persist_and_block_even_valid_code_until_resend(client, registration):
    pending, code = begin(client, registration)
    wrong = '000000' if code != '000000' else '999999'
    for attempt in range(settings.otp_max_attempts):
        response = verify(client, pending, wrong)
        assert response.status_code == (429 if attempt + 1 == settings.otp_max_attempts else 400)
        with SessionLocal() as db:
            assert db.get(StudentRegistration, pending['challenge_id']).attempts == attempt + 1
    assert verify(client, pending, code).status_code == 429
    allow_resend(pending)
    assert client.post('/api/v1/auth/resend-verification', json={'challenge_id': pending['challenge_id']}).status_code == 200
    new_code = latest_code(pending)
    assert new_code != code
    with SessionLocal() as db:
        assert db.get(StudentRegistration, pending['challenge_id']).attempts == 0
    assert verify(client, pending, new_code).status_code == 201


def test_expired_code_can_be_replaced_but_previous_code_is_invalid(client, registration):
    pending, code = begin(client, registration)
    with SessionLocal() as db:
        db.get(StudentRegistration, pending['challenge_id']).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert verify(client, pending, code).json()['detail'] == registration_service.CODE_EXPIRED
    allow_resend(pending)
    response = client.post('/api/v1/auth/resend-verification', json={'challenge_id': pending['challenge_id']})
    assert response.status_code == 200, response.text
    assert verify(client, pending, code).status_code == 400
    assert verify(client, pending, latest_code(pending)).status_code == 201
    with SessionLocal() as db:
        assert all(code not in mail.text_body for mail in db.scalars(select(MailOutbox)))


def test_resend_cooldown_prevents_new_mail_and_password_replacement(client, registration):
    pending, code = begin(client, registration)
    response = client.post('/api/v1/auth/resend-verification', json={'challenge_id': pending['challenge_id']})
    assert response.status_code == 429 and int(response.headers['Retry-After']) > 0
    duplicate = client.post('/api/v1/auth/register', json={**registration, 'password': 'Attacker-replacement!'})
    assert duplicate.status_code == 429
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(MailOutbox)) == 1
        assert verify_password(PASSWORD, db.get(StudentRegistration, pending['challenge_id']).password_hash)
    assert verify(client, pending, code).status_code == 201


def test_restarted_signup_gets_new_challenge_and_cannot_reuse_victim_page(client, registration):
    pending, code = begin(client, registration)
    allow_resend(pending)
    replacement, new_code = begin(client, {**registration, 'password': 'Replacement-password!'})
    assert replacement['challenge_id'] != pending['challenge_id']
    assert verify(client, pending, code).status_code == 400
    assert verify(client, pending, new_code).status_code == 400
    assert verify(client, replacement, new_code).status_code == 201
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == registration['email']))
        assert verify_password('Replacement-password!', user.password_hash)


@pytest.mark.parametrize('endpoint', ['verify-email', 'resend-verification'])
def test_registration_lifetime_is_limited_and_purges_expired_payload(client, registration, endpoint):
    pending, code = begin(client, registration)
    with SessionLocal() as db:
        db.get(StudentRegistration, pending['challenge_id']).created_at = utcnow() - timedelta(hours=25)
        db.commit()
    response = client.post(f'/api/v1/auth/{endpoint}', json={'challenge_id': pending['challenge_id'], **({'code': code} if endpoint == 'verify-email' else {})})
    assert response.status_code == 400 and response.json()['detail'] == registration_service.REGISTRATION_EXPIRED
    with SessionLocal() as db:
        assert db.get(StudentRegistration, pending['challenge_id']) is None
        assert code not in db.scalar(select(MailOutbox)).text_body


@pytest.mark.parametrize('change', ['campus-archived', 'campus-deleted', 'registration-closed'])
def test_verification_rechecks_campus_and_registration_policy(client, registration, data, monkeypatch, change):
    pending, code = begin(client, registration)
    if change == 'registration-closed':
        monkeypatch.setattr(settings, 'public_registration_enabled', False)
    else:
        with SessionLocal() as db:
            campus = db.get(Campus, data['campus_a'])
            if change == 'campus-archived':
                campus.status = 'ARCHIVED'
            else:
                campus.deleted_at = utcnow()
            db.commit()
    assert verify(client, pending, code).status_code == (403 if change == 'registration-closed' else 404)
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == registration['email'])) is None


def test_verification_rolls_back_all_authority_if_welcome_queue_fails(client, registration, monkeypatch):
    pending, code = begin(client, registration)
    original = registration_service.queue_email
    def reject_mail(db, *args, **kwargs):
        db.flush()
        raise IntegrityError('test failure', {}, Exception('simulated'))
    monkeypatch.setattr(registration_service, 'queue_email', reject_mail)
    assert verify(client, pending, code).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == registration['email'])) is None
        assert db.scalar(select(func.count()).select_from(CampusMembership)) == 4
        assert db.scalar(select(func.count()).select_from(RoleAssignment)) == 5
        assert db.get(StudentRegistration, pending['challenge_id']) is not None
        assert db.scalar(select(MailOutbox)).status == 'PENDING'
    monkeypatch.setattr(registration_service, 'queue_email', original)
    assert verify(client, pending, code).status_code == 201


def test_new_email_ownership_during_pending_period_is_not_overwritten(client, registration):
    pending, code = begin(client, registration)
    with SessionLocal() as db:
        record = db.get(StudentRegistration, pending['challenge_id'])
        db.add(User(email=record.email, first_name='Invité', last_name='Admin', password_hash=record.password_hash))
        db.commit()
    response = verify(client, pending, code)
    assert response.status_code == 409 and response.json()['detail'] == registration_service.EMAIL_USED
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == registration['email']))
        assert user.first_name == 'Invité' and user.email_verified_at is None
        assert db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user.id)) is None


def test_stale_revision_cannot_consume_or_overwrite_new_code(client, registration):
    pending, _ = begin(client, registration)
    with SessionLocal() as stale:
        old = stale.get(StudentRegistration, pending['challenge_id'])
        allow_resend(pending)
        assert client.post('/api/v1/auth/resend-verification', json={'challenge_id': pending['challenge_id']}).status_code == 200
        with pytest.raises(HTTPException) as error:
            registration_service._claim(stale, old)
        assert error.value.status_code == 409
        stale.rollback()
    assert verify(client, pending, latest_code(pending)).status_code == 201


def test_mail_rate_limit_is_shared_by_register_and_resend(client, registration):
    pending, _ = begin(client, registration)
    for _ in range(4):
        allow_resend(pending)
        assert client.post('/api/v1/auth/resend-verification', json={'challenge_id': pending['challenge_id']}).status_code == 200
    allow_resend(pending)
    response = client.post('/api/v1/auth/resend-verification', json={'challenge_id': pending['challenge_id']})
    assert response.status_code == 429 and int(response.headers['Retry-After']) > 0
    assert client.post('/api/v1/auth/register', json=registration).status_code == 429
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(MailOutbox).where(MailOutbox.status == 'PENDING')) == 1


def test_email_verification_rate_limit_survives_challenge_restart(client, registration):
    pending, _ = begin(client, registration)
    # Requests against a locked code must still consume the email limit.
    for _ in range(30):
        verify(client, pending, '000000')
    response = verify(client, pending, latest_code(pending))
    assert response.status_code == 429 and 'Retry-After' in response.headers
    allow_resend(pending)
    replacement, code = begin(client, registration)
    response = verify(client, replacement, code)
    assert response.status_code == 429 and 'Retry-After' in response.headers


@pytest.mark.parametrize('code', ['12345', '1234567', 'abcdef', '１２３４５６'])
def test_only_six_ascii_digits_are_accepted(client, registration, code):
    pending, _ = begin(client, registration)
    assert verify(client, pending, code).status_code == 422


def test_unknown_challenge_cannot_create_account(client, registration):
    assert verify(client, {'challenge_id': str(uuid4())}, '123456').status_code == 400
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == registration['email'])) is None


def test_smtp_disabled_never_bypasses_verification(client, registration, monkeypatch):
    monkeypatch.setattr(settings, 'smtp_enabled', False)
    pending, code = begin(client, registration)
    assert client.post('/api/v1/auth/login', json={'email': registration['email'], 'password': PASSWORD}).status_code == 401
    assert verify(client, pending, code).status_code == 201


def test_worker_cleanup_purges_abandoned_password_hash_and_otp(client, registration):
    pending, code = begin(client, registration)
    with SessionLocal() as db:
        assert registration_service.purge_expired_registrations(db) == 0
        db.get(StudentRegistration, pending['challenge_id']).created_at = utcnow() - timedelta(hours=25)
        db.commit()
        assert registration_service.purge_expired_registrations(db) == 1
        db.commit()
        assert db.get(StudentRegistration, pending['challenge_id']) is None
        mail = db.scalar(select(MailOutbox))
        assert mail.status == 'CANCELLED' and code not in mail.text_body
        assert registration_service.purge_expired_registrations(db) == 0


def test_hmac_binds_code_to_challenge_and_secret(monkeypatch):
    monkeypatch.setattr(settings, 'otp_secret_key', 'a' * 40)
    digest = registration_service.code_digest('challenge-a', '123456')
    assert digest != registration_service.code_digest('challenge-b', '123456')
    monkeypatch.setattr(settings, 'otp_secret_key', 'b' * 40)
    assert digest != registration_service.code_digest('challenge-a', '123456')


@pytest.mark.parametrize('options', [dict(otp_ttl_minutes=0), dict(otp_ttl_minutes=31), dict(otp_max_attempts=0), dict(otp_max_attempts=11), dict(otp_resend_cooldown_seconds=0)])
def test_otp_settings_are_bounded(options):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **options)
