"""Transactional SMTP outbox. Never log reset URLs or credentials."""
import logging
import smtplib
import ssl
from datetime import datetime, timedelta
from html import escape
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


def branded_email(title: str, preheader: str, greeting: str, paragraphs: list[str], *, button_text: str | None = None, button_url: str | None = None, verification_code: str | None = None) -> str:
    """Responsive, email-client-safe CampusPulse HTML with a plain inline footer."""
    safe_title = escape(title)
    safe_greeting = escape(greeting)
    safe_paragraphs = ''.join(
        f'<p style="margin:0 0 16px;color:#43515c;font-size:15px;line-height:1.7">{escape(paragraph).replace(chr(10), "<br>")}</p>'
        for paragraph in paragraphs
    )
    cta = ''
    if button_text and button_url:
        cta = (f'<p style="margin:28px 0"><a href="{escape(button_url, quote=True)}" '
               f'style="display:inline-block;background:#126b65;color:#fff;text-decoration:none;font-weight:700;'
               f'padding:14px 22px;border-radius:10px">{escape(button_text)}</a></p>')
    code_card = ''
    if verification_code:
        code_card = (f'<div style="margin:25px 0;padding:18px;text-align:center;background:#f0f7f4;border:1px solid #d9ebe3;'
                     f'border-radius:12px;color:#145f57;font-size:30px;font-weight:700;letter-spacing:8px">{escape(verification_code)}</div>')
    year = utcnow().year
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{safe_title}</title></head><body style="margin:0;background:#f2f5f3;font-family:Arial,Helvetica,sans-serif">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{escape(preheader)}</div>'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f2f5f3;padding:32px 12px"><tr><td align="center">'
        '<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:100%;max-width:600px;background:#fff;border-radius:18px;overflow:hidden">'
        '<tr><td style="background:#123c3a;padding:25px 32px"><div style="color:#fff;font-size:22px;font-weight:700;letter-spacing:-.4px">Campus<span style="color:#86d3bd">Pulse</span></div>'
        '<div style="margin-top:6px;color:#b9d4cd;font-size:11px;letter-spacing:1.5px">LE CAMPUS QUI VOUS RELIE</div></td></tr>'
        f'<tr><td style="padding:34px 32px 22px"><h1 style="margin:0 0 23px;color:#183c3a;font-size:25px;line-height:1.25">{safe_title}</h1>'
        f'<p style="margin:0 0 16px;color:#43515c;font-size:15px;line-height:1.7">Bonjour {safe_greeting},</p>{safe_paragraphs}{code_card}{cta}'
        '<p style="margin:25px 0 0;color:#43515c;font-size:15px;line-height:1.7">À bientôt sur votre campus,<br><strong>L’équipe CampusPulse</strong></p></td></tr>'
        f'<tr><td style="padding:19px 32px;background:#f8faf9;border-top:1px solid #e7eeea;color:#718078;font-size:12px;line-height:1.7">'
        f'<strong style="color:#315a50">Tolojanahary</strong> · © {year} CampusPulse<br>Ce message automatique concerne votre compte CampusPulse. '
        'Si vous n’êtes pas à l’origine de cette demande, vous pouvez ignorer ce courriel.</td></tr>'
        '</table></td></tr></table></body></html>'
    )


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
