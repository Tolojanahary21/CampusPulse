"""Relational domain model. UUIDs are portable strings (PostgreSQL and SQLite)."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class Entity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Entity, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSession(Entity, Base):
    __tablename__ = 'user_sessions'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))


class PasswordResetToken(Entity, Base):
    __tablename__ = 'password_reset_tokens'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudentRegistration(Entity, Base):
    """Unverified signups have no user, session, membership or role."""
    __tablename__ = 'student_registrations'
    __table_args__ = (CheckConstraint('attempts >= 0', name='registration_attempts_positive'),)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resend_available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    mail_id: Mapped[str | None] = mapped_column(ForeignKey('mail_outbox.id'))


class Campus(Entity, Base):
    __tablename__ = 'campuses'
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default='Madagascar')
    logo_url: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampusMembership(Entity, Base):
    __tablename__ = 'campus_memberships'
    __table_args__ = (UniqueConstraint('user_id', 'campus_id'),)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    membership_type: Mapped[str] = mapped_column(String(30), default='STUDENT')
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RoleAssignment(Entity, Base):
    __tablename__ = 'role_assignments'
    __table_args__ = (
        CheckConstraint("(role = 'PLATFORM_ADMIN' AND campus_id IS NULL) OR (role IN ('CAMPUS_ADMIN','CONTENT_PUBLISHER','MODERATOR','STUDENT') AND campus_id IS NOT NULL)", name='role_scope'),
        Index('uq_active_campus_role', 'user_id', 'campus_id', 'role', unique=True,
              sqlite_where=text('revoked_at IS NULL AND campus_id IS NOT NULL'),
              postgresql_where=text('revoked_at IS NULL AND campus_id IS NOT NULL')),
        Index('uq_active_global_role', 'user_id', 'role', unique=True,
              sqlite_where=text('revoked_at IS NULL AND campus_id IS NULL'),
              postgresql_where=text('revoked_at IS NULL AND campus_id IS NULL')),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    role: Mapped[str] = mapped_column(String(40))
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'), index=True)
    granted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Entity, Base):
    __tablename__ = 'notification_preferences'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), unique=True)
    email_announcements: Mapped[bool] = mapped_column(Boolean, default=True)
    email_community: Mapped[bool] = mapped_column(Boolean, default=False)


class AcademicYear(Entity, Base):
    __tablename__ = 'academic_years'
    __table_args__ = (
        UniqueConstraint('campus_id', 'name'), UniqueConstraint('id', 'campus_id', name='uq_academic_year_campus'),
        CheckConstraint('starts_on < ends_on', name='year_dates'),
        Index('uq_current_academic_year', 'campus_id', unique=True, sqlite_where=text('is_current = 1'), postgresql_where=text('is_current = true')),
    )
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    name: Mapped[str] = mapped_column(String(50))
    starts_on: Mapped[datetime] = mapped_column(Date)
    ends_on: Mapped[datetime] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class Program(Entity, Base):
    __tablename__ = 'programs'
    __table_args__ = (UniqueConstraint('campus_id', 'code'),)
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')


class ProgramLevel(Entity, Base):
    __tablename__ = 'program_levels'
    __table_args__ = (UniqueConstraint('program_id', 'code'), CheckConstraint('level_order > 0', name='level_positive_order'))
    program_id: Mapped[str] = mapped_column(ForeignKey('programs.id'), index=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    level_order: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')


class Subject(Entity, Base):
    __tablename__ = 'subjects'
    __table_args__ = (UniqueConstraint('program_level_id', 'code'), CheckConstraint('credits IS NULL OR credits >= 0', name='credits_positive'))
    program_level_id: Mapped[str] = mapped_column(ForeignKey('program_levels.id'), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    credits: Mapped[float | None] = mapped_column(Float)
    semester: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')


class Enrollment(Entity, Base):
    __tablename__ = 'enrollments'
    __table_args__ = (
        UniqueConstraint('user_id', 'program_level_id', 'academic_year_id'), UniqueConstraint('campus_id', 'enrollment_number'),
        ForeignKeyConstraint(['academic_year_id', 'campus_id'], ['academic_years.id', 'academic_years.campus_id'], name='fk_enrollment_year_campus'),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    program_level_id: Mapped[str] = mapped_column(ForeignKey('program_levels.id'), index=True)
    academic_year_id: Mapped[str] = mapped_column(ForeignKey('academic_years.id'), index=True)
    enrollment_number: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))


class CampusSettings(Entity, Base):
    __tablename__ = 'campus_settings'
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), unique=True)
    allow_announcement_comments: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_student_posts: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_student_comments: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_student_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, default=20)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))


class Announcement(Entity, Base):
    __tablename__ = 'announcements'
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(250))
    summary: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    announcement_type: Mapped[str] = mapped_column(String(30), default='GENERAL')
    scope: Mapped[str] = mapped_column(String(20), default='CAMPUS')
    status: Mapped[str] = mapped_column(String(20), default='DRAFT', index=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notifications_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    program_targets: Mapped[list['AnnouncementProgramTarget']] = relationship(cascade='all, delete-orphan', lazy='selectin')
    level_targets: Mapped[list['AnnouncementLevelTarget']] = relationship(cascade='all, delete-orphan', lazy='selectin')
    year_targets: Mapped[list['AnnouncementYearTarget']] = relationship(cascade='all, delete-orphan', lazy='selectin')
    program_ids = association_proxy('program_targets', 'program_id', creator=lambda v: AnnouncementProgramTarget(program_id=v))
    level_ids = association_proxy('level_targets', 'program_level_id', creator=lambda v: AnnouncementLevelTarget(program_level_id=v))
    year_ids = association_proxy('year_targets', 'academic_year_id', creator=lambda v: AnnouncementYearTarget(academic_year_id=v))


class AnnouncementProgramTarget(Base):
    __tablename__ = 'announcement_program_targets'
    announcement_id: Mapped[str] = mapped_column(ForeignKey('announcements.id'), primary_key=True)
    program_id: Mapped[str] = mapped_column(ForeignKey('programs.id'), primary_key=True)


class AnnouncementLevelTarget(Base):
    __tablename__ = 'announcement_level_targets'
    announcement_id: Mapped[str] = mapped_column(ForeignKey('announcements.id'), primary_key=True)
    program_level_id: Mapped[str] = mapped_column(ForeignKey('program_levels.id'), primary_key=True)


class AnnouncementYearTarget(Base):
    __tablename__ = 'announcement_year_targets'
    announcement_id: Mapped[str] = mapped_column(ForeignKey('announcements.id'), primary_key=True)
    academic_year_id: Mapped[str] = mapped_column(ForeignKey('academic_years.id'), primary_key=True)


class AnnouncementComment(Entity, Base):
    __tablename__ = 'announcement_comments'
    announcement_id: Mapped[str] = mapped_column(ForeignKey('announcements.id'), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='VISIBLE')


class Event(Entity, Base):
    __tablename__ = 'events'
    __table_args__ = (CheckConstraint('starts_at < ends_at', name='event_dates'),)
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'), index=True)
    announcement_id: Mapped[str | None] = mapped_column(ForeignKey('announcements.id'), unique=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(250))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    registration_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='DRAFT')


class FileAsset(Entity, Base):
    __tablename__ = 'file_assets'
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'), index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(150))
    extension: Mapped[str] = mapped_column(String(20))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256_hash: Mapped[str] = mapped_column(String(64))
    storage_provider: Mapped[str] = mapped_column(String(30), default='LOCAL')
    status: Mapped[str] = mapped_column(String(20), default='AVAILABLE')


class Document(Entity, Base):
    __tablename__ = 'documents'
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'), index=True)
    file_asset_id: Mapped[str] = mapped_column(ForeignKey('file_assets.id'), index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    subject_id: Mapped[str | None] = mapped_column(ForeignKey('subjects.id'))
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), default='COURSE')
    scope: Mapped[str] = mapped_column(String(20), default='CAMPUS')
    status: Mapped[str] = mapped_column(String(20), default='DRAFT', index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    program_targets: Mapped[list['DocumentProgramTarget']] = relationship(cascade='all, delete-orphan', lazy='selectin')
    level_targets: Mapped[list['DocumentLevelTarget']] = relationship(cascade='all, delete-orphan', lazy='selectin')
    year_targets: Mapped[list['DocumentYearTarget']] = relationship(cascade='all, delete-orphan', lazy='selectin')
    program_ids = association_proxy('program_targets', 'program_id', creator=lambda v: DocumentProgramTarget(program_id=v))
    level_ids = association_proxy('level_targets', 'program_level_id', creator=lambda v: DocumentLevelTarget(program_level_id=v))
    year_ids = association_proxy('year_targets', 'academic_year_id', creator=lambda v: DocumentYearTarget(academic_year_id=v))


class DocumentProgramTarget(Base):
    __tablename__ = 'document_program_targets'
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), primary_key=True)
    program_id: Mapped[str] = mapped_column(ForeignKey('programs.id'), primary_key=True)


class DocumentLevelTarget(Base):
    __tablename__ = 'document_level_targets'
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), primary_key=True)
    program_level_id: Mapped[str] = mapped_column(ForeignKey('program_levels.id'), primary_key=True)


class DocumentYearTarget(Base):
    __tablename__ = 'document_year_targets'
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), primary_key=True)
    academic_year_id: Mapped[str] = mapped_column(ForeignKey('academic_years.id'), primary_key=True)


class CommunityPost(Entity, Base):
    __tablename__ = 'community_posts'
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str | None] = mapped_column(String(250))
    content: Mapped[str] = mapped_column(Text)
    post_type: Mapped[str] = mapped_column(String(30), default='DISCUSSION')
    status: Mapped[str] = mapped_column(String(20), default='VISIBLE')


class CommunityComment(Entity, Base):
    __tablename__ = 'community_comments'
    post_id: Mapped[str] = mapped_column(ForeignKey('community_posts.id'), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    parent_comment_id: Mapped[str | None] = mapped_column(ForeignKey('community_comments.id'))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='VISIBLE')


class Reaction(Entity, Base):
    __tablename__ = 'reactions'
    __table_args__ = (UniqueConstraint('user_id', 'post_id'), UniqueConstraint('user_id', 'comment_id'), CheckConstraint('(post_id IS NULL) <> (comment_id IS NULL)', name='reaction_single_target'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    post_id: Mapped[str | None] = mapped_column(ForeignKey('community_posts.id'), index=True)
    comment_id: Mapped[str | None] = mapped_column(ForeignKey('community_comments.id'), index=True)
    reaction_type: Mapped[str] = mapped_column(String(20), default='LIKE')


class Report(Entity, Base):
    __tablename__ = 'reports'
    __table_args__ = (CheckConstraint('(post_id IS NULL) <> (comment_id IS NULL)', name='report_single_target'),)
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    reporter_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    post_id: Mapped[str | None] = mapped_column(ForeignKey('community_posts.id'))
    comment_id: Mapped[str | None] = mapped_column(ForeignKey('community_comments.id'))
    reason: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='OPEN')
    resolved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModerationAction(Entity, Base):
    __tablename__ = 'moderation_actions'
    campus_id: Mapped[str] = mapped_column(ForeignKey('campuses.id'), index=True)
    moderator_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    report_id: Mapped[str | None] = mapped_column(ForeignKey('reports.id'))
    post_id: Mapped[str | None] = mapped_column(ForeignKey('community_posts.id'))
    comment_id: Mapped[str | None] = mapped_column(ForeignKey('community_comments.id'))
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)


class Notification(Entity, Base):
    __tablename__ = 'notifications'
    __table_args__ = (UniqueConstraint('user_id', 'event_key'),)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'))
    event_key: Mapped[str] = mapped_column(String(150))
    notification_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(250))
    message: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(String(500))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Entity, Base):
    __tablename__ = 'audit_logs'
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    campus_id: Mapped[str | None] = mapped_column(ForeignKey('campuses.id'), index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class PlatformSetting(Entity, Base):
    __tablename__ = 'platform_settings'
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
