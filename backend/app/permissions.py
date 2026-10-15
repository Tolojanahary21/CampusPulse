"""Authorization rules shared by every API. No authorization depends on UI state."""
from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.inspection import inspect
from app.models import (AcademicYear, Announcement, AuditLog, Campus, CampusMembership, Document, Enrollment, Program, ProgramLevel, RoleAssignment, User, utcnow)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def valid_roles(db, user):
    now = utcnow()
    return [r for r in db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.revoked_at.is_(None)))
            if r.expires_at is None or aware(r.expires_at) > now]


def is_platform_admin(db, user):
    return user.status == 'ACTIVE' and any(r.role == 'PLATFORM_ADMIN' and r.campus_id is None for r in valid_roles(db, user))


def campus_member(db, user, campus_id):
    campus = db.get(Campus, campus_id)
    return bool(user.status == 'ACTIVE' and campus and campus.status == 'ACTIVE' and db.scalar(select(CampusMembership.id).where(
        CampusMembership.user_id == user.id, CampusMembership.campus_id == campus_id, CampusMembership.status == 'ACTIVE'))
        and any(role.campus_id == campus_id for role in valid_roles(db, user)))


def has_role(db, user, campus_id, *roles):
    if is_platform_admin(db, user):
        return True
    return bool(campus_id and campus_member(db, user, campus_id) and any(
        r.campus_id == campus_id and r.role in roles for r in valid_roles(db, user)))


def require_role(db, user, campus_id, *roles):
    if campus_id is not None and db.get(Campus, campus_id) is None:
        raise HTTPException(404, 'Établissement introuvable.')
    if not has_role(db, user, campus_id, *roles):
        raise HTTPException(403, 'Vous ne disposez pas des permissions nécessaires.')


def require_campus(db, user, campus_id):
    if not db.get(Campus, campus_id):
        raise HTTPException(404, 'Établissement introuvable.')
    if not is_platform_admin(db, user) and not campus_member(db, user, campus_id):
        raise HTTPException(403, 'Accès à cet établissement refusé.')


def accessible_campus_ids(db, user):
    if is_platform_admin(db, user):
        return list(db.scalars(select(Campus.id)))
    role_campuses = {role.campus_id for role in valid_roles(db, user)}
    return [ident for ident in db.scalars(select(CampusMembership.campus_id).join(Campus).where(
        CampusMembership.user_id == user.id, CampusMembership.status == 'ACTIVE', Campus.status == 'ACTIVE')) if ident in role_campuses]


def can_manage_content(db, user, obj):
    return has_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')


def can_view_content(db, user, obj, *, management=False):
    if management and can_manage_content(db, user, obj):
        return True
    if obj.status != 'PUBLISHED':
        return False
    if isinstance(obj, Announcement):
        now = utcnow()
        if obj.starts_at and aware(obj.starts_at) > now or obj.ends_at and aware(obj.ends_at) <= now:
            return False
    if obj.scope == 'PLATFORM':
        return True
    if not (is_platform_admin(db, user) or campus_member(db, user, obj.campus_id)):
        return False
    if obj.scope == 'CAMPUS' or can_manage_content(db, user, obj):
        return True
    if not (obj.program_ids or obj.level_ids or obj.year_ids):
        return False
    statuses = ['ACTIVE', 'COMPLETED'] if isinstance(obj, Document) else ['ACTIVE']
    enrollments = db.scalars(select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.campus_id == obj.campus_id, Enrollment.status.in_(statuses)))
    # All populated dimensions MUST match the SAME enrollment, never a union of journeys.
    for enrollment in enrollments:
        level = db.get(ProgramLevel, enrollment.program_level_id)
        if (not obj.program_ids or level.program_id in obj.program_ids) and (not obj.level_ids or level.id in obj.level_ids) and (not obj.year_ids or enrollment.academic_year_id in obj.year_ids):
            return True
    return False


def serialize(obj):
    forbidden = {'password_hash', 'storage_key', 'token_hash', 'csrf_token', 'code_hash'}
    result = {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs if c.key not in forbidden}
    if isinstance(obj, (Announcement, Document)):
        result.update(program_ids=list(obj.program_ids), level_ids=list(obj.level_ids), year_ids=list(obj.year_ids))
    return result


def audit(db, user, action, entity_type, entity_id, campus_id=None, details=None):
    record = AuditLog(actor_user_id=user.id if user else None, action=action, entity_type=entity_type,
                      entity_id=entity_id, campus_id=campus_id, details=details or {})
    db.add(record)
    return record
