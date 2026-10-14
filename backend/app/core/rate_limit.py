"""Database-backed limits shared by every API worker; no raw IP/email stored."""
import hashlib
import hmac
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import DateTime, Integer, String, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.security import as_utc, utcnow
from app.db.base import Base


class AuthRateLimit(Base):
    __tablename__ = 'auth_rate_limits'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)


def check_rate_limit(db, namespace: str, identifier: str, limit: int = 10, minutes: int = 15):
    now = utcnow()
    key = hmac.new(settings.secret_key.encode(), f'{namespace}:{identifier}'.encode(), hashlib.sha256).hexdigest()
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.expires_at <= now))
    db.commit()
    entry = db.scalar(select(AuthRateLimit).where(AuthRateLimit.key == key).with_for_update())
    if entry is None:
        entry = AuthRateLimit(key=key, count=0, expires_at=now + timedelta(minutes=minutes))
        db.add(entry)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    result = db.execute(update(AuthRateLimit).where(AuthRateLimit.key == key, AuthRateLimit.count < limit).values(count=AuthRateLimit.count + 1))
    db.commit()
    if result.rowcount == 0:
        entry = db.get(AuthRateLimit, key)
        retry = max(1, int((as_utc(entry.expires_at) - now).total_seconds())) if entry else 60
        raise HTTPException(429, 'Trop de tentatives. Réessayez dans quelques minutes.', headers={'Retry-After': str(retry)})
