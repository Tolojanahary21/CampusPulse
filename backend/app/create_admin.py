"""Explicit production bootstrap: python -m app.create_admin --email ..."""
import argparse
import getpass
import os

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, utcnow
from app.db.session import SessionLocal
from app.models import RoleAssignment, User
from app.permissions import audit


def main():
    parser = argparse.ArgumentParser(description='Créer explicitement un administrateur de plateforme.')
    parser.add_argument('--email', required=True)
    parser.add_argument('--first-name', default='Administrateur')
    parser.add_argument('--last-name', default='CampusPulse')
    args = parser.parse_args()
    try:
        email = validate_email(args.email, check_deliverability=False, test_environment=settings.app_env != 'production').normalized.lower()
    except EmailNotValidError as error:
        parser.error(str(error))
    password = os.getenv('ADMIN_BOOTSTRAP_PASSWORD') or getpass.getpass('Mot de passe (12 caractères minimum) : ')
    if len(password) < 12 or len(password) > 128:
        parser.error('Le mot de passe doit contenir de 12 à 128 caractères.')
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            parser.error('Ce compte existe déjà. Aucun compte ou rôle existant n’a été modifié.')
        user = User(email=email, first_name=args.first_name, last_name=args.last_name, password_hash=hash_password(password), email_verified_at=utcnow())
        db.add(user)
        db.flush()
        db.add(RoleAssignment(user_id=user.id, role='PLATFORM_ADMIN', campus_id=None))
        audit(db, user, 'PLATFORM_ADMIN_BOOTSTRAPPED', 'user', user.id)
        db.commit()
    print('Administrateur créé. Vous pouvez vous connecter avec ses identifiants.')


if __name__ == '__main__':
    main()
