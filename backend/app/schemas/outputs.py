"""Typed public API projections generated from columns, excluding private fields.

The projection remains distinct from ORM serialization: extra fields are filtered by
the response validator and only explicitly declared enrichments can leave the API.
"""
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy.inspection import inspect
from app import models

PRIVATE = {'password_hash', 'storage_key', 'token_hash', 'csrf_token', 'notifications_dispatched_at'}
ENRICHMENTS = {
    'Announcement': {'program_ids': (list[str], []), 'level_ids': (list[str], []), 'year_ids': (list[str], []), 'campus_name': (str | None, None)},
    'Document': {'program_ids': (list[str], []), 'level_ids': (list[str], []), 'year_ids': (list[str], []),
                 'original_filename': (str | None, None), 'mime_type': (str | None, None), 'size_bytes': (int | None, None)},
    'Enrollment': {name: (str, ...) for name in ('student_name', 'student_email', 'program_name', 'level_name', 'academic_year_name', 'campus_name')},
    'CommunityPost': {'author_name': (str, ...), 'comment_count': (int, ...), 'reaction_count': (int, ...), 'my_reaction_id': (str | None, None)},
    'AnnouncementComment': {'author_name': (str, ...)},
    'CommunityComment': {'author_name': (str, ...)},
    'Report': {'post_title': (str | None, None), 'content': (str | None, None), 'reporter_name': (str | None, None)},
}


def output_model(name):
    model = getattr(models, name)
    fields = {}
    for column in inspect(model).columns:
        if column.name in PRIVATE:
            continue
        field_type = column.type.python_type
        fields[column.name] = (field_type | None, None) if column.nullable else (field_type, ...)
    fields.update(ENRICHMENTS.get(name, {}))
    # Ignore non-public fields if an ORM serializer receives new columns later.
    return create_model(f'{name}Output', __config__=ConfigDict(extra='ignore', from_attributes=True), **fields)


for name in ('Campus', 'RoleAssignment', 'User', 'AuditLog', 'CampusSettings', 'AcademicYear', 'Program',
             'ProgramLevel', 'Subject', 'Enrollment', 'Announcement', 'AnnouncementComment', 'Document', 'FileAsset',
             'Event', 'CommunityPost', 'CommunityComment', 'Reaction', 'Report', 'ModerationAction', 'Notification'):
    globals()[f'{name}Output'] = output_model(name)


Item = TypeVar('Item')


class CollectionOutput(BaseModel, Generic[Item]):
    items: list[Item]
    total: int
    page: int
    page_size: int


class MessageOutput(BaseModel):
    message: str


class DashboardOutput(BaseModel):
    campuses: int
    students: int
    announcements: int
    documents: int
    events: int
    posts: int
    unread_notifications: int
    pending_reports: int
    enrollments: int


class ActivityOutput(BaseModel):
    id: str
    type: str
    title: str
    created_at: datetime
    link: str
    campus_id: str | None
