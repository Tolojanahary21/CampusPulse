"""Mandatory email OTP for public signup. Pending records cannot authenticate."""
import hashlib
import hmac
import math
import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import as_utc, hash_password, hash_token, utcnow
from app.models import Campus, CampusMembership, RegistrationLink, RoleAssignment, StudentRegistration, User
from app.permissions import audit
from app.services.mail import MailOutbox, branded_email, queue_email

CLOSED = 'Les inscriptions étudiantes sont temporairement fermées. Contactez votre établissement.'
CAMPUS_UNAVAILABLE = 'Cet établissement ne propose pas d’inscription actuellement.'
EMAIL_USED = 'Cette adresse est déjà utilisée.'
INVALID_CHALLENGE = 'Cette vérification est introuvable ou terminée. Recommencez votre inscription.'
REGISTRATION_EXPIRED = 'Cette inscription a expiré. Recommencez votre inscription.'
CODE_EXPIRED = 'Ce code a expiré. Demandez un nouveau code.'
CODE_INVALID = 'Le code de vérification est incorrect.'
TOO_MANY_ATTEMPTS = 'Trop de codes incorrects. Demandez un nouveau code.'
COOLDOWN = 'Veuillez patienter avant de demander un nouveau code.'
CONCURRENT_CHANGE = 'La vérification a changé. Utilisez le dernier code reçu ou recommencez votre inscription.'
PERSISTENCE_FAILED = 'L’inscription n’a pas pu être enregistrée. Réessayez.'
QUEUED = 'Un code de vérification a été mis en attente d’envoi à votre adresse e-mail.'
VERIFIED = 'Votre adresse e-mail est vérifiée. Vous pouvez maintenant vous connecter.'
REGISTRATION_LIFETIME = timedelta(hours=24)


def code_digest(challenge_id: str, code: str) -> str:
    key = settings.otp_secret_key or settings.secret_key
    return hmac.new(key.encode(), f'student-registration:{challenge_id}:{code}'.encode(), hashlib.sha256).hexdigest()


def metadata(registration):
    return {
        'verification_required': True,
        'challenge_id': registration.id,
        'email': registration.email,
        'expires_at': as_utc(registration.expires_at),
        'resend_available_at': as_utc(registration.resend_available_at),
        'message': QUEUED,
    }


def _active_campus(db, campus_id):
    if not settings.public_registration_enabled:
        raise HTTPException(403, CLOSED)
    campus = db.scalar(select(Campus).where(Campus.id == campus_id, Campus.status == 'ACTIVE', Campus.deleted_at.is_(None)).with_for_update(read=True))
    if campus is None:
        raise HTTPException(404, CAMPUS_UNAVAILABLE)
    return campus


def _cancel_mail(db, registration):
    if registration.mail_id:
        # The worker holds the same mail row lock while delivering; after this
        # update commits it can never pick an obsolete code from the outbox.
        db.execute(update(MailOutbox).where(MailOutbox.id == registration.mail_id).values(
            status='CANCELLED', text_body='[Vérification terminée ou remplacée ; contenu purgé]', html_body=None,
        ))


def _discard(db, registration):
    _cancel_mail(db, registration)
    db.delete(registration)
    db.flush()


def purge_expired_registrations(db, batch_size=100):
    """Purge abandoned signup credentials; caller commits with other worker jobs."""
    expired = db.scalars(select(StudentRegistration).where(
        StudentRegistration.created_at <= utcnow() - REGISTRATION_LIFETIME,
    ).order_by(StudentRegistration.created_at, StudentRegistration.id).limit(batch_size).with_for_update(skip_locked=True)).all()
    for registration in expired:
        _discard(db, registration)
    return len(expired)


def _cooldown(registration, now):
    seconds = math.ceil((as_utc(registration.resend_available_at) - now).total_seconds())
    if seconds > 0:
        raise HTTPException(429, COOLDOWN, headers={'Retry-After': str(seconds)})


def _claim(db, registration):
    # Row locks protect PostgreSQL. Compare-and-swap additionally makes a stale
    # request unable to consume or overwrite another verification on SQLite.
    changed = db.execute(update(StudentRegistration).where(
        StudentRegistration.id == registration.id,
        StudentRegistration.revision == registration.revision,
    ).values(revision=StudentRegistration.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise HTTPException(409, CONCURRENT_CHANGE)
    db.refresh(registration)


def _pending(db, challenge_id):
    registration = db.scalar(select(StudentRegistration).where(StudentRegistration.id == challenge_id).with_for_update().execution_options(populate_existing=True))
    if registration is None:
        raise HTTPException(400, INVALID_CHALLENGE)
    if as_utc(registration.created_at) + REGISTRATION_LIFETIME <= utcnow():
        _discard(db, registration)
        db.commit()
        raise HTTPException(400, REGISTRATION_EXPIRED)
    return registration


def _queue_code(db, registration, now):
    previous = registration.code_hash
    while True:
        code = f'{secrets.randbelow(1_000_000):06d}'
        digest = code_digest(registration.id, code)
        if previous is None or not hmac.compare_digest(previous, digest):
            break
    registration.code_hash = digest
    registration.expires_at = now + timedelta(minutes=settings.otp_ttl_minutes)
    registration.resend_available_at = now + timedelta(seconds=settings.otp_resend_cooldown_seconds)
    registration.attempts = 0
    subject = 'Votre code de vérification CampusPulse'
    text_body = (
        f'Bonjour {registration.first_name},\n\n'
        'Pour confirmer votre adresse e-mail et créer votre compte CampusPulse :\n\n'
        f'Code : {code}\n\n'
        f'Ce code est personnel, à usage unique et expire dans {settings.otp_ttl_minutes} minutes. '
        'Saisissez-le dans la page d’inscription. Ne partagez pas ce code.\n'
        'Si vous n’êtes pas à l’origine de cette inscription, ignorez ce message.\n\nL’équipe CampusPulse'
    )
    html_body = branded_email(
        'Confirmez votre adresse e-mail', 'Votre code CampusPulse est prêt.', registration.first_name,
        [f'Utilisez ce code à usage unique pour confirmer votre adresse e-mail. Il expire dans {settings.otp_ttl_minutes} minutes.',
         'Saisissez-le dans la page d’inscription. Ne le partagez avec personne.'],
        verification_code=code,
    )
    registration.mail_id = queue_email(
        db, registration.email, subject, text_body, html_body,
        expires_at=registration.expires_at,
    )


def start_registration(db, data):
    # Hash before acquiring locks; never store or mail the submitted password.
    password_hash = hash_password(data.password)
    try:
        role = 'STUDENT'
        link_id = None
        if data.invitation_token:
            invitation = db.scalar(select(RegistrationLink).where(
                RegistrationLink.token_hash == hash_token(data.invitation_token),
            ).with_for_update())
            if invitation is None or invitation.consumed_at is not None or as_utc(invitation.expires_at) <= utcnow():
                raise HTTPException(400, 'Ce lien d’inscription est invalide ou a expiré. Demandez un nouveau lien.')
            role = invitation.role
            link_id = invitation.id
            if data.campus_id != invitation.campus_id:
                raise HTTPException(422, 'Cet établissement ne correspond pas au lien reçu.')
        campus = _active_campus(db, data.campus_id)
        if db.scalar(select(User.id).where(User.email == data.email)):
            raise HTTPException(409, EMAIL_USED)
        previous = db.scalar(select(StudentRegistration).where(StudentRegistration.email == data.email).with_for_update())
        now = utcnow()
        if previous:
            _cooldown(previous, now)
            _claim(db, previous)
            _discard(db, previous)
        registration = StudentRegistration(
            email=data.email, campus_id=campus.id, first_name=data.first_name, last_name=data.last_name,
            password_hash=password_hash, code_hash='', expires_at=now, resend_available_at=now,
            role=role, registration_link_id=link_id,
        )
        db.add(registration)
        db.flush()
        _queue_code(db, registration, now)
        db.commit()
        return metadata(registration)
    except IntegrityError as exc:
        db.rollback()
        message = EMAIL_USED if db.scalar(select(User.id).where(User.email == data.email)) else PERSISTENCE_FAILED
        raise HTTPException(409, message) from exc


def resend_verification(db, challenge_id):
    registration = _pending(db, challenge_id)
    _active_campus(db, registration.campus_id)
    if db.scalar(select(User.id).where(User.email == registration.email)):
        _discard(db, registration)
        db.commit()
        raise HTTPException(409, EMAIL_USED)
    now = utcnow()
    _cooldown(registration, now)
    _claim(db, registration)
    _cancel_mail(db, registration)
    try:
        _queue_code(db, registration, now)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, PERSISTENCE_FAILED) from exc
    return metadata(registration)


def verify_registration(db, challenge_id, code):
    registration = _pending(db, challenge_id)
    campus = _active_campus(db, registration.campus_id)
    now = utcnow()
    if registration.attempts >= settings.otp_max_attempts:
        raise HTTPException(429, TOO_MANY_ATTEMPTS)
    if as_utc(registration.expires_at) <= now:
        _cancel_mail(db, registration)
        db.commit()
        raise HTTPException(400, CODE_EXPIRED)
    expected = code_digest(registration.id, code)
    valid = hmac.compare_digest(registration.code_hash, expected)
    _claim(db, registration)
    if not valid:
        registration.attempts += 1
        locked = registration.attempts >= settings.otp_max_attempts
        if locked:
            _cancel_mail(db, registration)
        # Persist failed attempts even though the endpoint returns an error.
        db.commit()
        raise HTTPException(429 if locked else 400, TOO_MANY_ATTEMPTS if locked else CODE_INVALID)
    email = registration.email
    try:
        if registration.registration_link_id:
            link = db.scalar(select(RegistrationLink).where(
                RegistrationLink.id == registration.registration_link_id,
            ).with_for_update())
            if link is None or link.role != registration.role or link.campus_id != registration.campus_id or link.consumed_at is not None or as_utc(link.expires_at) <= now:
                _discard(db, registration)
                db.commit()
                raise HTTPException(400, 'Ce lien d’inscription a déjà été utilisé ou a expiré.')
            consumed = db.execute(update(RegistrationLink).where(
                RegistrationLink.id == link.id,
                RegistrationLink.consumed_at.is_(None),
                RegistrationLink.expires_at > now,
            ).values(consumed_at=now).execution_options(synchronize_session=False))
            if consumed.rowcount != 1:
                _discard(db, registration)
                db.commit()
                raise HTTPException(400, 'Ce lien d’inscription a déjà été utilisé ou a expiré.')
        if db.scalar(select(User.id).where(User.email == email)):
            _discard(db, registration)
            db.commit()
            raise HTTPException(409, EMAIL_USED)
        user = User(
            email=email, first_name=registration.first_name, last_name=registration.last_name,
            password_hash=registration.password_hash, status='ACTIVE', email_verified_at=now,
        )
        db.add(user)
        db.flush()
        db.add(CampusMembership(user_id=user.id, campus_id=campus.id, membership_type='STUDENT' if registration.role == 'STUDENT' else 'STAFF', status='ACTIVE'))
        db.add(RoleAssignment(user_id=user.id, campus_id=campus.id, role=registration.role))
        role_label = {'STUDENT': 'étudiant', 'CAMPUS_ADMIN': 'administrateur d’établissement', 'CONTENT_PUBLISHER': 'responsable de publication', 'MODERATOR': 'modérateur'}.get(registration.role, 'membre')
        welcome = f'Votre adresse e-mail est vérifiée. Votre compte {role_label} est activé pour {campus.name}.'
        login_url = f'{settings.frontend_url}/login'
        queue_email(db, user.email, 'Bienvenue sur CampusPulse',
                    f'Bonjour {user.first_name},\n\n{welcome}\n\nConnectez-vous : {login_url}\n\nL’équipe CampusPulse',
                    branded_email('Bienvenue sur CampusPulse', 'Votre adresse e-mail est confirmée.', user.first_name,
                                  [welcome], button_text='Se connecter', button_url=login_url))
        audit(db, user, 'STUDENT_REGISTERED' if registration.role == 'STUDENT' else 'ROLE_REGISTERED',
              'user', user.id, campus_id=campus.id, details={'email_verified': True, 'role': registration.role})
        _discard(db, registration)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = EMAIL_USED if db.scalar(select(User.id).where(User.email == email)) else PERSISTENCE_FAILED
        raise HTTPException(409, message) from exc
    return {'message': VERIFIED}
