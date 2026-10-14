"""Run `python -m app.mail_worker [--once | --retry-failed]`."""
import argparse
import logging
import time

from sqlalchemy import update

from app.core.config import settings
from app.core.security import utcnow
from app.db.session import SessionLocal
from app.services.mail import MailOutbox, process_outbox
from app.services.notifications import process_due_announcements


def main():
    parser = argparse.ArgumentParser(description='File d’attente SMTP CampusPulse')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--retry-failed', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.retry_failed:
        with SessionLocal() as db:
            result = db.execute(update(MailOutbox).where(MailOutbox.status == 'FAILED', MailOutbox.expires_at > utcnow()).values(status='PENDING', attempts=0, next_attempt_at=utcnow()))
            db.commit()
            print(f'{result.rowcount} message(s) remis en attente.')
        return
    try:
        while True:
            with SessionLocal() as db:
                scheduled = process_due_announcements(db)
                db.commit()
            counts = process_outbox()
            if args.once:
                print({**counts, **scheduled})
                return
            time.sleep(settings.mail_poll_seconds)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
