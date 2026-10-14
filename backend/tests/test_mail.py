import smtplib
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.core.config import Settings, settings
from app.db.session import SessionLocal
from app.services.mail import MailOutbox, process_outbox, queue_email, send_email


def test_outbox_retries_then_purges_sensitive_content(monkeypatch):
    monkeypatch.setattr(settings, 'smtp_enabled', True)
    with SessionLocal() as db:
        mail_id = queue_email(db, 'student@example.com', 'Test SMTP', 'Secret reset URL')
        db.commit()
    with patch('app.services.mail.send_email', side_effect=smtplib.SMTPServerDisconnected('offline')):
        assert process_outbox() == {'sent':0,'failed':1}
    with SessionLocal() as db:
        mail = db.get(MailOutbox, mail_id)
        assert mail.status == 'PENDING' and mail.attempts == 1
        assert mail.last_error == 'SMTPServerDisconnected'
        from app.core.security import utcnow
        mail.next_attempt_at = utcnow()
        db.commit()
    with patch('app.services.mail.send_email') as sender:
        assert process_outbox() == {'sent':1,'failed':0}
        sender.assert_called_once()
    with SessionLocal() as db:
        mail = db.get(MailOutbox, mail_id)
        assert mail.status == 'SENT'
        assert 'Secret' not in mail.text_body


def test_starttls_authenticated_smtp(monkeypatch):
    monkeypatch.setattr(settings, 'smtp_starttls', True)
    monkeypatch.setattr(settings, 'smtp_ssl', False)
    monkeypatch.setattr(settings, 'smtp_username', 'mailer')
    monkeypatch.setattr(settings, 'smtp_password', 'smtp-test-password')
    with patch('app.services.mail.smtplib.SMTP') as constructor:
        smtp = constructor.return_value.__enter__.return_value
        send_email('student@example.com', 'Bonjour', 'Texte du message')
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with('mailer', 'smtp-test-password')
        message = smtp.send_message.call_args.args[0]
        assert message['To'] == 'student@example.com'
        assert 'Texte du message' in message.get_content()


def test_production_configuration_requires_https_and_real_secret():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env='production', secret_key='change-me', cookie_secure=False)


def test_expired_mail_is_purged_even_if_delivery_disabled():
    from datetime import timedelta
    from app.core.security import utcnow
    with SessionLocal() as db:
        ident = queue_email(db,'student@example.com','Expired','Sensitive expired link',expires_at=utcnow()-timedelta(seconds=1))
        db.commit()
    process_outbox()
    with SessionLocal() as db:
        mail = db.get(MailOutbox,ident)
        assert mail.status == 'EXPIRED'
        assert 'Sensitive' not in mail.text_body


def test_real_smtp_delivery_to_local_test_server(monkeypatch):
    """Actual SMTP protocol against an isolated loopback receiver; no external mail."""
    import socket
    from aiosmtpd.controller import Controller
    from email import policy
    from email.parser import BytesParser

    class Receiver:
        messages = []

        async def handle_DATA(self, server, session, envelope):
            self.messages.append(envelope.original_content)
            return '250 Message accepted'

    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1', 0))
        port = port_socket.getsockname()[1]
    receiver = Receiver()
    controller = Controller(receiver, hostname='127.0.0.1', port=port)
    controller.start()
    try:
        monkeypatch.setattr(settings,'smtp_enabled',True)
        monkeypatch.setattr(settings,'smtp_host','127.0.0.1')
        monkeypatch.setattr(settings,'smtp_port',port)
        monkeypatch.setattr(settings,'smtp_username','')
        monkeypatch.setattr(settings,'smtp_password','')
        monkeypatch.setattr(settings,'smtp_ssl',False)
        monkeypatch.setattr(settings,'smtp_starttls',False)
        with SessionLocal() as db:
            queue_email(db,'student@example.com','Invitation CampusPulse','Bonjour, votre compte est prêt.')
            db.commit()
        assert process_outbox()['sent'] == 1
        parsed = BytesParser(policy=policy.default).parsebytes(receiver.messages[0])
        assert parsed['Subject'] == 'Invitation CampusPulse'
        assert parsed['To'] == 'student@example.com'
        assert 'votre compte est prêt' in parsed.get_content()
    finally:
        controller.stop()
