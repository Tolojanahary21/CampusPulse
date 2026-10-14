from datetime import timedelta
from typing import Annotated, Literal

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limit import check_rate_limit
from app.core.security import as_utc, hash_password, hash_token, new_token, password_hasher, utcnow, verify_password
from app.db.session import get_db
from app.models import Campus, CampusMembership, NotificationPreference, PasswordResetToken, RoleAssignment, StudentRegistration, User, UserSession
from app.permissions import audit, is_platform_admin, require_role
from app.services.mail import queue_email
from app.services.registration import resend_verification, start_registration, verify_registration

router = APIRouter(tags=['Authentification et comptes'])
# Equalize expensive password verification for missing accounts.
_DUMMY_PASSWORD_HASH = hash_password(new_token())
Password = Annotated[str, StringConstraints(strip_whitespace=False)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class EmailInput(Input):
    email: str = Field(max_length=255)

    @field_validator('email')
    @classmethod
    def normalized_email(cls, value):
        try:
            return validate_email(value.strip(), check_deliverability=False, test_environment=settings.app_env != 'production').normalized.lower()
        except EmailNotValidError as exc:
            raise ValueError('Adresse e-mail invalide.') from exc


class LoginInput(EmailInput):
    password: Password = Field(min_length=1, max_length=128)


class ResetInput(Input):
    token: str = Field(min_length=20, max_length=200)
    password: Password = Field(min_length=12, max_length=128)


class ProfileInput(Input):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)


class RegisterInput(EmailInput):
    campus_id: str = Field(min_length=1, max_length=36)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: Password = Field(min_length=12, max_length=128)


class RegistrationChallengeInput(Input):
    challenge_id: str = Field(min_length=36, max_length=36, pattern=r'^[0-9a-f-]{36}$')


class VerifyEmailInput(RegistrationChallengeInput):
    code: str = Field(pattern=r'^[0-9]{6}$')


class ChangePasswordInput(Input):
    current_password: Password = Field(min_length=1, max_length=128)
    new_password: Password = Field(min_length=12, max_length=128)


class PreferencesInput(Input):
    email_announcements: bool
    email_community: bool


class InvitationInput(EmailInput):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: Literal['STUDENT', 'CONTENT_PUBLISHER', 'MODERATOR', 'CAMPUS_ADMIN'] = 'STUDENT'


class MembershipStatusInput(Input):
    status: Literal['ACTIVE', 'SUSPENDED', 'ENDED']


def profile(db: Session, user: User) -> dict:
    now = utcnow()
    roles = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.revoked_at.is_(None), or_(RoleAssignment.expires_at.is_(None), RoleAssignment.expires_at > now))).all()
    campus_query = select(Campus).where(Campus.status == 'ACTIVE')
    if not any(role.role == 'PLATFORM_ADMIN' for role in roles):
        campus_query = campus_query.join(CampusMembership, CampusMembership.campus_id == Campus.id).where(CampusMembership.user_id == user.id, CampusMembership.status == 'ACTIVE')
    campuses = db.scalars(campus_query.order_by(Campus.name)).all()
    active_ids = {c.id for c in campuses}
    return {
        'id': user.id, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name,
        'phone': user.phone, 'avatar_url': user.avatar_url, 'status': user.status,
        'email_verified_at': user.email_verified_at, 'created_at': user.created_at,
        'roles': [{'id': r.id, 'role': r.role, 'campus_id': r.campus_id} for r in roles if r.campus_id is None or r.campus_id in active_ids],
        'campuses': [{'id': c.id, 'name': c.name, 'code': c.code} for c in campuses],
    }


def clear_cookies(response: Response):
    for name in (settings.session_cookie_name, 'campuspulse_csrf'):
        response.delete_cookie(name, path='/', domain=settings.cookie_domain, secure=settings.cookie_secure, samesite='lax')


def revoke_sessions(db, user_id):
    db.execute(update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)).values(revoked_at=utcnow()))


def issue_reset(db, user, invitation=False):
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    now = utcnow()
    # Only the newest recovery link remains usable.
    db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).values(used_at=now))
    token = new_token()
    ttl = timedelta(hours=settings.invitation_expire_hours) if invitation else timedelta(minutes=settings.password_reset_expire_minutes)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=now + ttl))
    route = 'accept-invitation' if invitation else 'reset-password'
    link = f'{settings.frontend_url}/{route}?token={token}'
    subject = 'Bienvenue sur CampusPulse' if invitation else 'Réinitialisez votre mot de passe CampusPulse'
    text = f'Bonjour {user.first_name},\n\n'
    text += 'Votre établissement vous invite à rejoindre CampusPulse.\n' if invitation else 'Une demande de réinitialisation de votre mot de passe a été reçue.\n'
    text += f'\nChoisissez votre mot de passe :\n{link}\n\nCe lien est personnel, à usage unique et expire dans {int(ttl.total_seconds() / 60)} minutes.\nSi vous n’êtes pas à l’origine de cette demande, ignorez ce message.\n\nL’équipe CampusPulse'
    queue_email(db, user.email, subject, text, expires_at=now + ttl)


@router.post('/auth/login')
def login(data: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else 'unknown'
    check_rate_limit(db, 'login-ip', ip, 50)
    check_rate_limit(db, 'login-email', data.email, 10)
    user = db.scalar(select(User).where(User.email == data.email))
    valid = verify_password(data.password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    if not user or not valid or user.status != 'ACTIVE' or user.deleted_at:
        raise HTTPException(401, 'Adresse e-mail ou mot de passe incorrect.')
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    # Replace any session presented during login (no session fixation).
    previous = request.cookies.get(settings.session_cookie_name)
    if previous:
        db.execute(update(UserSession).where(UserSession.token_hash == hash_token(previous)).values(revoked_at=utcnow()))
    token, csrf = new_token(), new_token()
    now = utcnow()
    db.add(UserSession(user_id=user.id, token_hash=hash_token(token), csrf_token=csrf, expires_at=now + timedelta(hours=settings.session_expire_hours), ip_address=ip, user_agent=request.headers.get('user-agent', '')[:512], last_used_at=now))
    user.last_login_at = now
    db.commit()
    options = {'max_age': settings.session_expire_hours * 3600, 'secure': settings.cookie_secure, 'samesite': 'lax', 'path': '/', 'domain': settings.cookie_domain}
    response.set_cookie(settings.session_cookie_name, token, httponly=True, **options)
    response.set_cookie('campuspulse_csrf', csrf, httponly=False, **options)
    return profile(db, user)


@router.get('/auth/me')
@router.get('/users/me')
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile(db, user)


@router.post('/auth/logout', status_code=204)
def logout(request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    request.state.auth_session.revoked_at = utcnow()
    db.commit()
    clear_cookies(response)


@router.post('/auth/forgot-password')
def forgot_password(data: EmailInput, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(db, 'forgot-ip', request.client.host if request.client else 'unknown', 30)
    check_rate_limit(db, 'forgot-email', data.email, 5)
    user = db.scalar(select(User).where(User.email == data.email, User.status == 'ACTIVE', User.deleted_at.is_(None)))
    if user:
        issue_reset(db, user)
        db.commit()
    return {'message': 'Si un compte actif correspond à cette adresse, un lien de réinitialisation vous sera envoyé.'}


@router.post('/auth/reset-password')
@router.post('/auth/accept-invitation')
def reset_password(data: ResetInput, request: Request, response: Response, db: Session = Depends(get_db)):
    check_rate_limit(db, 'reset-ip', request.client.host if request.client else 'unknown', 20)
    reset = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(data.token), PasswordResetToken.used_at.is_(None)))
    if not reset or as_utc(reset.expires_at) <= utcnow():
        raise HTTPException(400, 'Ce lien est invalide ou a expiré. Demandez un nouveau lien.')
    user = db.scalar(select(User).where(User.id == reset.user_id).with_for_update())
    db.refresh(reset)
    if reset.used_at is not None:
        raise HTTPException(400, 'Ce lien a déjà été utilisé.')
    if not user or user.status != 'ACTIVE' or user.deleted_at:
        raise HTTPException(400, 'Ce lien ne peut plus être utilisé.')
    # Atomic consumption also protects SQLite tests and concurrent requests.
    consumed = db.execute(update(PasswordResetToken).where(PasswordResetToken.id == reset.id, PasswordResetToken.used_at.is_(None)).values(used_at=utcnow()))
    if consumed.rowcount != 1:
        raise HTTPException(400, 'Ce lien a déjà été utilisé.')
    user.password_hash = hash_password(data.password)
    user.email_verified_at = user.email_verified_at or utcnow()
    revoke_sessions(db, user.id)
    db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).values(used_at=utcnow()))
    audit(db, user, 'PASSWORD_RESET', 'user', user.id)
    db.commit()
    clear_cookies(response)
    return {'message': 'Votre mot de passe a été enregistré. Vous pouvez vous connecter.'}


@router.get('/auth/registration-options')
def registration_options(db: Session = Depends(get_db)):
    if not settings.public_registration_enabled:
        return {'enabled': False, 'campuses': []}
    campuses = db.scalars(select(Campus).where(Campus.status == 'ACTIVE', Campus.deleted_at.is_(None)).order_by(Campus.name, Campus.id)).all()
    return {'enabled': True, 'campuses': [{'id': campus.id, 'name': campus.name, 'code': campus.code} for campus in campuses]}


@router.post('/auth/register', status_code=202)
def register(data: RegisterInput, request: Request, db: Session = Depends(get_db)):
    if not settings.public_registration_enabled:
        raise HTTPException(403, 'Les inscriptions étudiantes sont temporairement fermées. Contactez votre établissement.')
    check_rate_limit(db, 'register-ip', request.client.host if request.client else 'unknown', 5, 60)
    check_rate_limit(db, 'registration-mail-email', data.email, 5, 60)
    return start_registration(db, data)


def registration_limits(db, request, challenge_id, *, resend=False):
    # This limiter commits. It must run before acquiring any signup/mail lock.
    namespace = 'resend-verification' if resend else 'verify-email'
    check_rate_limit(db, f'{namespace}-ip', request.client.host if request.client else 'unknown', 20 if resend else 60, 60 if resend else 15)
    email = db.scalar(select(StudentRegistration.email).where(StudentRegistration.id == challenge_id))
    if email:
        check_rate_limit(db, 'registration-mail-email' if resend else 'verify-email-address', email, 5 if resend else 30, 60 if resend else 15)


@router.post('/auth/verify-email', status_code=201)
def verify_email(data: VerifyEmailInput, request: Request, db: Session = Depends(get_db)):
    registration_limits(db, request, data.challenge_id)
    return verify_registration(db, data.challenge_id, data.code)


@router.post('/auth/resend-verification')
def resend_email_verification(data: RegistrationChallengeInput, request: Request, db: Session = Depends(get_db)):
    registration_limits(db, request, data.challenge_id, resend=True)
    return resend_verification(db, data.challenge_id)


@router.patch('/users/me')
def update_me(data: ProfileInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for key, value in data.model_dump().items():
        setattr(user, key, value)
    db.commit()
    return profile(db, user)


@router.patch('/users/me/password')
def change_password(data: ChangePasswordInput, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_rate_limit(db, 'change-password', user.id, 5)
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, 'Le mot de passe actuel est incorrect.')
    user.password_hash = hash_password(data.new_password)
    revoke_sessions(db, user.id)
    db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).values(used_at=utcnow()))
    audit(db, user, 'PASSWORD_CHANGED', 'user', user.id)
    db.commit()
    clear_cookies(response)
    return {'message': 'Mot de passe modifié. Reconnectez-vous.'}


@router.get('/notification-preferences')
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
    return {'email_announcements': prefs.email_announcements if prefs else True, 'email_community': prefs.email_community if prefs else False}


@router.patch('/notification-preferences')
def update_preferences(data: PreferencesInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user.id))
    if not prefs:
        prefs = NotificationPreference(user_id=user.id)
        db.add(prefs)
    for key, value in data.model_dump().items():
        setattr(prefs, key, value)
    db.commit()
    return data.model_dump()


def campus_user_data(db, user, campus_id):
    membership = db.scalar(select(CampusMembership).where(CampusMembership.user_id == user.id, CampusMembership.campus_id == campus_id))
    roles = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.campus_id == campus_id, RoleAssignment.revoked_at.is_(None), or_(RoleAssignment.expires_at.is_(None), RoleAssignment.expires_at > utcnow()))).all()
    return {'id': user.id, 'email': user.email, 'first_name': user.first_name, 'last_name': user.last_name, 'status': user.status, 'membership_status': membership.status if membership else None, 'roles': [{'id': r.id, 'role': r.role, 'campus_id': r.campus_id} for r in roles], 'created_at': user.created_at}


@router.get('/campuses/{campus_id}/users')
def list_campus_users(campus_id: str, q: str = '', page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    query = select(User).join(CampusMembership, CampusMembership.user_id == User.id).where(CampusMembership.campus_id == campus_id)
    if q:
        pattern = f'%{q}%'
        query = query.where(or_(User.email.ilike(pattern), User.first_name.ilike(pattern), User.last_name.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    users = db.scalars(query.order_by(User.last_name, User.id).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': [campus_user_data(db, u, campus_id) for u in users], 'total': total, 'page': page, 'page_size': page_size}


@router.post('/campuses/{campus_id}/users', status_code=201)
def invite_user(campus_id: str, data: InvitationInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    if data.role == 'CAMPUS_ADMIN' and not is_platform_admin(db, user):
        raise HTTPException(403, 'Seule l’administration de plateforme peut nommer un administrateur.')
    target = db.scalar(select(User).where(User.email == data.email))
    is_new = target is None
    if is_new:
        target = User(email=data.email, first_name=data.first_name, last_name=data.last_name, password_hash=hash_password(new_token()))
        db.add(target)
        db.flush()
    elif target.status != 'ACTIVE' or target.deleted_at:
        raise HTTPException(409, 'Ce compte doit être réactivé par l’administration de plateforme.')
    membership = db.scalar(select(CampusMembership).where(CampusMembership.user_id == target.id, CampusMembership.campus_id == campus_id))
    if membership:
        raise HTTPException(409, 'Ce compte est déjà rattaché à cet établissement.')
    db.add(CampusMembership(user_id=target.id, campus_id=campus_id, membership_type='STUDENT' if data.role == 'STUDENT' else 'STAFF'))
    db.add(RoleAssignment(user_id=target.id, campus_id=campus_id, role=data.role, granted_by_user_id=user.id))
    if is_new:
        issue_reset(db, target, invitation=True)
    else:
        campus = db.get(Campus, campus_id)
        queue_email(db, target.email, 'Un nouvel établissement sur CampusPulse', f'Bonjour {target.first_name},\n\nVous avez rejoint {campus.name}. Retrouvez cet espace avec votre compte habituel :\n{settings.frontend_url}/login')
    audit(db, user, 'USER_INVITED', 'user', target.id, campus_id=campus_id, details={'role': data.role})
    db.commit()
    return campus_user_data(db, target, campus_id)


@router.post('/campuses/{campus_id}/users/{user_id}/resend-invitation')
def resend_invitation(campus_id: str, user_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    target = db.get(User, user_id)
    membership = db.scalar(select(CampusMembership).where(CampusMembership.user_id == user_id, CampusMembership.campus_id == campus_id))
    if not target or not membership or target.status != 'ACTIVE' or membership.status != 'ACTIVE':
        raise HTTPException(404, 'Invitation introuvable.')
    if target.email_verified_at is not None:
        raise HTTPException(409, 'Ce compte est déjà activé. Son titulaire peut demander une réinitialisation.')
    check_rate_limit(db, 'resend-invite', user_id, 3, 60)
    issue_reset(db, target, invitation=True)
    db.commit()
    return {'message': 'Une nouvelle invitation a été mise en attente d’envoi.'}


@router.patch('/campuses/{campus_id}/users/{user_id}/status')
def change_membership_status(campus_id: str, user_id: str, data: MembershipStatusInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    target = db.get(User, user_id)
    membership = db.scalar(select(CampusMembership).where(CampusMembership.user_id == user_id, CampusMembership.campus_id == campus_id))
    if not target or not membership:
        raise HTTPException(404, 'Compte introuvable dans cet établissement.')
    privileged = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user_id, RoleAssignment.role.in_(['PLATFORM_ADMIN', 'CAMPUS_ADMIN']), RoleAssignment.revoked_at.is_(None), or_(RoleAssignment.campus_id == campus_id, RoleAssignment.campus_id.is_(None))))
    if target.id == user.id or (privileged and not is_platform_admin(db, user)):
        raise HTTPException(403, 'Cette adhésion doit être gérée par un autre administrateur de plateforme.')
    membership.status = data.status
    membership.ended_at = utcnow() if data.status == 'ENDED' else None
    audit(db, user, 'MEMBERSHIP_STATUS_CHANGED', 'campus_membership', membership.id, campus_id=campus_id, details={'status':data.status})
    db.commit()
    return campus_user_data(db, target, campus_id)
