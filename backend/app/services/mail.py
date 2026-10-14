"""Transactional SMTP outbox. Never log reset URLs or credentials."""
import logging
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, select, update
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.security import utcnow
from app.db.base import Base
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class MailOutbox(Base):
    __tablename__ = 'mail_outbox'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    text_body: Mapped[str] = mapped_column(Text)
    html_body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='PENDING', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: utcnow() + timedelta(days=7), index=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(100))


def queue_email(db, to_email: str, subject: str, text_body: str, html_body: str | None = None, *, expires_at: datetime | None = None) -> str:
    mail = MailOutbox(recipient=to_email, subject=subject, text_body=text_body, html_body=html_body)
    if expires_at is not None:
        mail.expires_at = expires_at
    db.add(mail)
    db.flush()
    return mail.id


def send_email(recipient: str, subject: str, text_body: str, html_body: str | None = None, message_id: str | None = None):
    message = EmailMessage()
    message['From'] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message['To'] = recipient
    message['Subject'] = subject
    if message_id:
        message['Message-ID'] = f'<{message_id}@campuspulse.local>'
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype='html')
    options = {'host': settings.smtp_host, 'port': settings.smtp_port, 'timeout': settings.smtp_timeout_seconds}
    if settings.smtp_ssl:
        connection = smtplib.SMTP_SSL(**options, context=ssl.create_default_context())
    else:
        connection = smtplib.SMTP(**options)
    with connection as smtp:
        smtp.ehlo()
        if settings.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def process_outbox(batch_size: int = 20) -> dict:
    counts = {'sent': 0, 'failed': 0}
    with SessionLocal() as db:
        db.execute(update(MailOutbox).where(MailOutbox.status.in_(['PENDING', 'FAILED']), MailOutbox.expires_at <= utcnow()).values(status='EXPIRED', text_body='[Message expiré ; contenu purgé]', html_body=None))
        db.commit()
    if not settings.smtp_enabled:
        return counts
    # Lock one message at a time. PostgreSQL SKIP LOCKED supports several workers.
    for _ in range(batch_size):
        with SessionLocal() as db:
            mail = db.scalar(select(MailOutbox).where(MailOutbox.status == 'PENDING', MailOutbox.next_attempt_at <= utcnow()).order_by(MailOutbox.created_at).with_for_update(skip_locked=True).limit(1))
            if mail is None:
                break
            mail.attempts += 1
            try:
                send_email(mail.recipient, mail.subject, mail.text_body, mail.html_body, mail.id)
                mail.status = 'SENT'
                mail.sent_at = utcnow()
                mail.text_body = '[Message envoyé ; contenu purgé]'
                mail.html_body = None
                mail.last_error = None
                counts['sent'] += 1
            except (OSError, smtplib.SMTPException, ValueError) as error:
                mail.last_error = type(error).__name__
                mail.status = 'FAILED' if mail.attempts >= settings.mail_max_attempts else 'PENDING'
                mail.next_attempt_at = utcnow() + timedelta(seconds=min(3600, 30 * 2 ** mail.attempts))
                logger.warning('SMTP message %s: %s (attempt %s)', mail.id, mail.last_error, mail.attempts)
                counts['failed'] += 1
            db.commit()
    return counts
