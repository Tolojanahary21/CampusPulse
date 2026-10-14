import re

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import hash_password, utcnow, verify_password
from app.db.session import SessionLocal
from app.models import AuditLog, Campus, CampusMembership, PasswordResetToken, RoleAssignment, User
from app.services.mail import MailOutbox
from app.services import registration as registration_service
from tests.conftest import PASSWORD


@pytest.fixture
def registration(data, monkeypatch):
    monkeypatch.setattr(settings, 'public_registration_enabled', True)
    return {'email': 'nouveau@example.com', 'password': PASSWORD, 'first_name': 'Nouveau', 'last_name': 'Étudiant', 'campus_id': data['campus_a']}


def register_and_verify(client, registration):
    pending = client.post('/api/v1/auth/register', json=registration)
    assert pending.status_code == 202, pending.text
    with SessionLocal() as db:
        mail = db.scalar(select(MailOutbox).where(MailOutbox.recipient == registration['email'], MailOutbox.subject == 'Votre code de vérification CampusPulse'))
        code = re.search(r'Code : ([0-9]{6})', mail.text_body).group(1)
    verified = client.post('/api/v1/auth/verify-email', json={'challenge_id': pending.json()['challenge_id'], 'code': code})
    assert verified.status_code == 201, verified.text


def test_student_signup_can_login_in_selected_campus_only(client, registration, data):
    options = client.get('/api/v1/auth/registration-options')
    assert options.status_code == 200
    assert options.json() == {'enabled': True, 'campuses': [
        {'id': data['campus_a'], 'name': 'Université A', 'code': 'A'},
        {'id': data['campus_b'], 'name': 'Université B', 'code': 'B'},
    ]}
    register_and_verify(client, registration)
    logged_in = client.post('/api/v1/auth/login', json={'email': registration['email'], 'password': PASSWORD})
    assert logged_in.status_code == 200, logged_in.text
    profile = logged_in.json()
    assert profile['email_verified_at'] is not None
    assert [(role['role'], role['campus_id']) for role in profile['roles']] == [('STUDENT', data['campus_a'])]
    assert [campus['id'] for campus in profile['campuses']] == [data['campus_a']]
    assert [campus['id'] for campus in client.get('/api/v1/campuses').json()['items']] == [data['campus_a']]
    client.headers['X-CSRF-Token'] = client.cookies.get('campuspulse_csrf')
    assert client.post('/api/v1/community/posts', json={'campus_id': data['campus_a'], 'content': 'Bonjour mon établissement !'}).status_code == 201
    assert client.post('/api/v1/community/posts', json={'campus_id': data['campus_b'], 'content': 'Autre établissement'}).status_code == 403
    assert client.get('/api/v1/platform/users').status_code == 403
    with SessionLocal() as db:
        user = db.get(User, profile['id'])
        assert user.status == 'ACTIVE'
        assert user.password_hash != PASSWORD and verify_password(PASSWORD, user.password_hash)
        membership = db.scalar(select(CampusMembership).where(CampusMembership.user_id == user.id))
        assert (membership.membership_type, membership.status, membership.campus_id) == ('STUDENT', 'ACTIVE', data['campus_a'])
        assert db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)) is None
        mail = db.scalar(select(MailOutbox).where(MailOutbox.recipient == user.email, MailOutbox.subject == 'Bienvenue sur CampusPulse'))
        assert mail is not None and mail.status == 'PENDING'
        assert '/login' in mail.text_body and 'Université A' in mail.text_body
        assert 'token=' not in mail.text_body and PASSWORD not in mail.text_body
        assert db.scalar(select(AuditLog).where(AuditLog.action == 'STUDENT_REGISTERED', AuditLog.actor_user_id == user.id)) is not None


@pytest.mark.parametrize('campus_state', ['ARCHIVED', 'deleted', 'missing'])
def test_signup_rejects_unavailable_campuses_without_creating_account(client, registration, data, campus_state):
    with SessionLocal() as db:
        campus = db.get(Campus, data['campus_a'])
        if campus_state == 'deleted':
            campus.deleted_at = utcnow()
        elif campus_state == 'ARCHIVED':
            campus.status = 'ARCHIVED'
        db.commit()
    if campus_state == 'missing':
        registration['campus_id'] = 'unknown-campus'
    else:
        assert [campus['id'] for campus in client.get('/api/v1/auth/registration-options').json()['campuses']] == [data['campus_b']]
    assert client.post('/api/v1/auth/register', json=registration).status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == registration['email'])) is None
        assert db.scalar(select(MailOutbox)) is None


@pytest.mark.parametrize('field,value', [('role', 'PLATFORM_ADMIN'), ('status', 'ACTIVE'), ('membership_type', 'STAFF')])
def test_signup_rejects_fields_that_assign_privileges(client, registration, field, value):
    response = client.post('/api/v1/auth/register', json={**registration, field: value})
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == registration['email'])) is None


@pytest.mark.parametrize('campus_id', [None, '', '   '])
def test_signup_requires_an_explicit_campus(client, registration, campus_id):
    if campus_id is None:
        registration.pop('campus_id')
    else:
        registration['campus_id'] = campus_id
    assert client.post('/api/v1/auth/register', json=registration).status_code == 422


def test_duplicate_signup_preserves_account_and_membership(client, registration, data):
    register_and_verify(client, registration)
    duplicate = {**registration, 'email': registration['email'].upper(), 'campus_id': data['campus_b'], 'password': 'Replacement-password!'}
    assert client.post('/api/v1/auth/register', json=duplicate).status_code == 409
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == registration['email']))
        assert verify_password(PASSWORD, user.password_hash)
        memberships = db.scalars(select(CampusMembership).where(CampusMembership.user_id == user.id)).all()
        assert [membership.campus_id for membership in memberships] == [data['campus_a']]
        assert db.scalar(select(func.count()).select_from(MailOutbox).where(MailOutbox.recipient == user.email, MailOutbox.status == 'PENDING')) == 1


def test_signup_handles_email_claimed_after_duplicate_check(client, registration, monkeypatch):
    original_hash = registration_service.hash_password
    winner_hash = hash_password('Another-password!')

    def claim_email_while_hashing(password):
        # Simulate another request winning after our initial email lookup.
        with SessionLocal() as db:
            db.add(User(email=registration['email'], first_name='Premier', last_name='Inscrit', password_hash=winner_hash))
            db.commit()
        return original_hash(password)

    monkeypatch.setattr(registration_service, 'hash_password', claim_email_while_hashing)
    response = client.post('/api/v1/auth/register', json=registration)
    assert response.status_code == 409, response.text
    assert response.json()['detail'] == 'Cette adresse est déjà utilisée.'
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == registration['email']))
        assert user.first_name == 'Premier' and user.password_hash == winner_hash
        assert db.scalar(select(CampusMembership).where(CampusMembership.user_id == user.id)) is None
        assert db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user.id)) is None
        assert db.scalar(select(MailOutbox)) is None


def test_signup_rolls_back_account_membership_and_role_on_transaction_failure(client, registration, monkeypatch):
    def reject_mail(db, *args, **kwargs):
        db.flush()
        raise IntegrityError('mail persistence failed', {}, Exception('simulated conflict'))

    monkeypatch.setattr(registration_service, 'queue_email', reject_mail)
    assert client.post('/api/v1/auth/register', json=registration).status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == registration['email'])) is None
        assert db.scalar(select(func.count()).select_from(CampusMembership)) == 4
        assert db.scalar(select(func.count()).select_from(RoleAssignment)) == 5
        assert db.scalar(select(MailOutbox)) is None
        assert db.scalar(select(AuditLog).where(AuditLog.action == 'STUDENT_REGISTERED')) is None


def test_signup_attempts_are_rate_limited(client, registration):
    registration['email'] = 'student@example.com'
    for _ in range(5):
        assert client.post('/api/v1/auth/register', json=registration).status_code == 409
    response = client.post('/api/v1/auth/register', json=registration)
    assert response.status_code == 429
    assert int(response.headers['Retry-After']) > 0


@pytest.mark.parametrize('actor', ['anonymous', 'STUDENT', 'CONTENT_PUBLISHER', 'MODERATOR'])
def test_non_admin_cannot_create_privileged_accounts_or_grant_roles(client, login, data, actor):
    if actor != 'anonymous':
        if actor != 'STUDENT':
            with SessionLocal() as db:
                role = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == data['student']))
                role.role = actor
                db.commit()
        login('student')
    expected = 401 if actor == 'anonymous' else 403
    invitation = {'email': 'staff@example.com', 'first_name': 'Personnel', 'last_name': 'Campus', 'role': 'CONTENT_PUBLISHER'}
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/users", json=invitation).status_code == expected
    assert client.post(f"/api/v1/platform/campuses/{data['campus_a']}/admins", json={'user_id': data['student'], 'role': 'CAMPUS_ADMIN'}).status_code == expected
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == invitation['email'])) is None


def test_campus_admin_creates_staff_but_only_platform_admin_creates_campus_admin(client, login, data):
    invitation = {'email': 'staff@example.com', 'first_name': 'Personnel', 'last_name': 'Campus', 'role': 'CONTENT_PUBLISHER'}
    login('admin')
    response = client.post(f"/api/v1/campuses/{data['campus_a']}/users", json=invitation)
    assert response.status_code == 201, response.text
    assert [role['role'] for role in response.json()['roles']] == ['CONTENT_PUBLISHER']
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/users", json={**invitation, 'email': 'other-admin@example.com', 'role': 'CAMPUS_ADMIN'}).status_code == 403
    assert client.post(f"/api/v1/platform/campuses/{data['campus_a']}/admins", json={'user_id': data['student'], 'role': 'CAMPUS_ADMIN'}).status_code == 403
    login('platform')
    response = client.post(f"/api/v1/campuses/{data['campus_a']}/users", json={**invitation, 'email': 'other-admin@example.com', 'role': 'CAMPUS_ADMIN'})
    assert response.status_code == 201, response.text
    assert [role['role'] for role in response.json()['roles']] == ['CAMPUS_ADMIN']
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/users", json={**invitation, 'email': 'platform-admin@example.com', 'role': 'PLATFORM_ADMIN'}).status_code == 422
