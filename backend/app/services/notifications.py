"""Recipient authorization and durable dispatch of scheduled announcements."""
from sqlalchemy import or_, select

from app.core.config import settings
from app.models import Announcement, Notification, NotificationPreference, User, utcnow
from app.permissions import aware, can_view_content
from app.services.mail import queue_email


def notify_publication(db, obj):
    now = utcnow()
    if isinstance(obj, Announcement):
        if obj.starts_at and aware(obj.starts_at) > now or obj.ends_at and aware(obj.ends_at) <= now:
            return 0
    collection = 'announcements' if isinstance(obj, Announcement) else 'documents'
    key = f'{collection}:{obj.id}:published'
    count = 0
    for recipient in db.scalars(select(User).where(User.status == 'ACTIVE')):
        if not can_view_content(db, recipient, obj):
            continue
        if db.scalar(select(Notification.id).where(Notification.user_id == recipient.id, Notification.event_key == key)):
            continue
        link = f'/app/{collection}/{obj.id}'
        db.add(Notification(user_id=recipient.id, campus_id=obj.campus_id, event_key=key,
                            notification_type='ANNOUNCEMENT' if collection == 'announcements' else 'DOCUMENT',
                            title=obj.title, message='Une nouvelle annonce officielle est disponible.' if collection == 'announcements' else 'Une nouvelle ressource pédagogique est disponible.', link=link))
        count += 1
        if isinstance(obj, Announcement):
            preference = db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == recipient.id))
            if preference is None or preference.email_announcements:
                subject = f'CampusPulse — {" ".join(obj.title.splitlines())}'[:255]
                queue_email(db, recipient.email, subject,
                            f'Bonjour {recipient.first_name},\n\nUne annonce vous concerne : {obj.title}\n\nConsultez-la dans votre espace sécurisé : {settings.frontend_url.rstrip("/")}{link}\n\nCampusPulse')
    if isinstance(obj, Announcement):
        obj.notifications_dispatched_at = now
    db.flush()
    return count


def process_due_announcements(db, batch_size=20):
    """Run inside the caller's transaction; PostgreSQL locks avoid concurrent dispatch."""
    now = utcnow()
    due = list(db.scalars(select(Announcement).where(
        Announcement.status == 'PUBLISHED', Announcement.notifications_dispatched_at.is_(None),
        or_(Announcement.starts_at.is_(None), Announcement.starts_at <= now),
        or_(Announcement.ends_at.is_(None), Announcement.ends_at > now),
    ).order_by(Announcement.created_at).with_for_update(skip_locked=True).limit(batch_size)))
    count = sum(notify_publication(db, announcement) for announcement in due)
    return {'announcements': len(due), 'notifications': count}
