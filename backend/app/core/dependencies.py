import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import as_utc, hash_token, utcnow
from app.db.session import get_db
from app.models import User, UserSession


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(401, 'Connectez-vous pour continuer.')
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None)))
    if session is None or as_utc(session.expires_at) <= utcnow():
        raise HTTPException(401, 'Votre session a expiré. Reconnectez-vous.')
    user = db.get(User, session.user_id)
    if user is None or user.status != 'ACTIVE' or getattr(user, 'deleted_at', None):
        raise HTTPException(401, 'Ce compte est désactivé.')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        csrf = request.headers.get('X-CSRF-Token', '')
        if not csrf or not secrets.compare_digest(csrf, session.csrf_token):
            raise HTTPException(403, 'Jeton de sécurité manquant ou invalide. Rechargez la page.')
    request.state.auth_session = session
    return user
