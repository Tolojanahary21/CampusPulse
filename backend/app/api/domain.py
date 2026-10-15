"""CampusPulse REST domain API, transactional and scoped on every resource."""
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import *
from app.permissions import (accessible_campus_ids, audit, can_manage_content, can_view_content, campus_member,
                             has_role, is_platform_admin, require_campus, require_role, serialize)
from app.schemas.domain import *
from app.schemas.outputs import *
from app.services.storage import file_path, save_upload
from app.services.notifications import notify_publication

router = APIRouter(tags=['Domaines'])
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(get_current_user)]
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def get(db, model, ident):
    obj = db.get(model, ident)
    if obj is None:
        raise HTTPException(404, 'Ressource introuvable.')
    return obj


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Ces données existent déjà ou sont liées à une autre ressource.') from None


def pack(items, page=1, page_size=20):
    start = (page - 1) * page_size
    stop = start + page_size
    selected = []
    total = 0
    for total, item in enumerate(items, start=1):
        if start < total <= stop:
            selected.append(item)
    return {'items': selected, 'total': total, 'page': page, 'page_size': page_size}


def rows(db, model):
    # Stream large tables rather than materializing every ORM row at once.
    return db.scalars(select(model).order_by(model.created_at.desc()).execution_options(yield_per=250))


def changed(obj, payload, schema):
    current = {name: getattr(obj, name) for name in schema.model_fields}
    current.update(payload.model_dump(exclude_unset=True))
    try:
        return schema.model_validate(current).model_dump()
    except ValidationError as exc:
        raise HTTPException(422, '; '.join(error['msg'] for error in exc.errors())) from None


def apply(obj, values):
    for name, value in values.items():
        setattr(obj, name, value)


def saved(db, user, obj, action, campus_id=None):
    db.add(obj)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Ces données existent déjà ou sont incohérentes.') from None
    audit(db, user, action, obj.__tablename__, obj.id, campus_id)
    commit(db)
    db.refresh(obj)
    return serialize(obj)


def platform(db, user):
    require_role(db, user, None, 'PLATFORM_ADMIN')


def campus_settings(db, campus_id):
    value = db.scalar(select(CampusSettings).where(CampusSettings.campus_id == campus_id))
    if not value:
        value = CampusSettings(campus_id=campus_id)
        db.add(value)
        db.flush()
    return value


def level_campus(db, level):
    return get(db, Program, level.program_id).campus_id


def enrich_enrollment(db, item):
    result = serialize(item)
    student = get(db, User, item.user_id)
    level = get(db, ProgramLevel, item.program_level_id)
    result.update(student_name=f'{student.first_name} {student.last_name}', student_email=student.email,
                  program_name=get(db, Program, level.program_id).name, level_name=level.name,
                  academic_year_name=get(db, AcademicYear, item.academic_year_id).name,
                  campus_name=get(db, Campus, item.campus_id).name)
    return result


@router.get('/campuses')
def my_campuses(db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[CampusOutput]:
    allowed = accessible_campus_ids(db, user)
    return pack((serialize(c) for c in rows(db, Campus) if c.id in allowed), page, page_size)


@router.get('/platform/campuses')
def platform_campuses(db: DB, user: Actor, q: str = '', page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[CampusOutput]:
    platform(db, user)
    return pack((serialize(c) for c in rows(db, Campus) if q.casefold() in f'{c.name} {c.code}'.casefold()), page, page_size)


@router.post('/platform/campuses', status_code=201)
def create_campus(payload: CampusInput, db: DB, user: Actor) -> CampusOutput:
    platform(db, user)
    return saved(db, user, Campus(**payload.model_dump()), 'campus.create')


@router.get('/platform/campuses/{campus_id}')
def get_campus(campus_id: str, db: DB, user: Actor) -> CampusOutput:
    platform(db, user)
    return serialize(get(db, Campus, campus_id))


@router.patch('/platform/campuses/{campus_id}')
def update_campus(campus_id: str, payload: CampusPatch, db: DB, user: Actor) -> CampusOutput:
    platform(db, user)
    obj = get(db, Campus, campus_id)
    apply(obj, changed(obj, payload, CampusInput))
    return saved(db, user, obj, 'campus.update', campus_id)


@router.post('/platform/campuses/{campus_id}/admins', status_code=201)
def grant_role(campus_id: str, payload: RoleInput, db: DB, user: Actor) -> RoleAssignmentOutput:
    platform(db, user)
    get(db, Campus, campus_id)
    target = get(db, User, payload.user_id)
    if target.status != 'ACTIVE':
        raise HTTPException(422, 'Le compte doit être actif.')
    membership = db.scalar(select(CampusMembership).where(CampusMembership.campus_id == campus_id, CampusMembership.user_id == target.id))
    if membership:
        membership.status = 'ACTIVE'
    else:
        db.add(CampusMembership(campus_id=campus_id, user_id=target.id, membership_type='STAFF'))
    duplicate = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == target.id, RoleAssignment.campus_id == campus_id,
                          RoleAssignment.role == payload.role, RoleAssignment.revoked_at.is_(None)))
    if duplicate:
        raise HTTPException(409, 'Ce rôle est déjà attribué. Révoquez-le avant de le renouveler.')
    return saved(db, user, RoleAssignment(campus_id=campus_id, granted_by_user_id=user.id, **payload.model_dump()), 'role.grant', campus_id)


@router.get('/campuses/{campus_id}/roles')
def list_roles(campus_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[RoleAssignmentOutput]:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    return pack((serialize(r) for r in rows(db, RoleAssignment) if r.campus_id == campus_id and r.revoked_at is None), page, page_size)


@router.delete('/roles/{role_id}', status_code=204)
def revoke_role(role_id: str, db: DB, user: Actor):
    obj = get(db, RoleAssignment, role_id)
    platform(db, user)
    if obj.role == 'PLATFORM_ADMIN' and obj.user_id == user.id:
        raise HTTPException(409, 'Vous ne pouvez pas révoquer votre propre accès plateforme.')
    obj.revoked_at = utcnow()
    saved(db, user, obj, 'role.revoke', obj.campus_id)
    return Response(status_code=204)


@router.get('/platform/users')
def platform_users(db: DB, user: Actor, q: str = '', page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[UserOutput]:
    platform(db, user)
    needle = q.casefold()
    return pack((serialize(u) for u in rows(db, User) if needle in f'{u.first_name} {u.last_name} {u.email}'.casefold()), page, page_size)


@router.patch('/platform/users/{user_id}/status')
def update_user_status(user_id: str, payload: UserStatusInput, db: DB, user: Actor) -> UserOutput:
    platform(db, user)
    if user_id == user.id and payload.status != 'ACTIVE':
        raise HTTPException(409, 'Vous ne pouvez pas désactiver votre propre compte.')
    obj = get(db, User, user_id)
    obj.status = payload.status
    if obj.status != 'ACTIVE':
        for session in db.scalars(select(UserSession).where(UserSession.user_id == obj.id, UserSession.revoked_at.is_(None))):
            session.revoked_at = utcnow()
    return saved(db, user, obj, 'user.status')


@router.get('/platform/audit-logs')
def audit_logs(db: DB, user: Actor, campus_id: str | None = None, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[AuditLogOutput]:
    if campus_id:
        require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    else:
        platform(db, user)
    return pack((serialize(a) for a in rows(db, AuditLog) if not campus_id or a.campus_id == campus_id), page, page_size)


@router.get('/platform/settings')
def get_platform_settings(db: DB, user: Actor) -> PlatformSettingsInput:
    platform(db, user)
    obj = db.scalar(select(PlatformSetting).where(PlatformSetting.key == 'general'))
    return obj.value if obj else PlatformSettingsInput().model_dump()


@router.patch('/platform/settings')
def update_platform_settings(payload: PlatformSettingsInput, db: DB, user: Actor) -> PlatformSettingsInput:
    platform(db, user)
    obj = db.scalar(select(PlatformSetting).where(PlatformSetting.key == 'general')) or PlatformSetting(key='general')
    obj.value = payload.model_dump()
    obj.updated_by_user_id = user.id
    saved(db, user, obj, 'platform.settings')
    return obj.value


@router.get('/campuses/{campus_id}/settings')
def get_campus_settings(campus_id: str, db: DB, user: Actor) -> CampusSettingsOutput:
    require_campus(db, user, campus_id)
    obj = campus_settings(db, campus_id)
    commit(db)
    return serialize(obj)


@router.patch('/campuses/{campus_id}/settings')
def update_campus_settings(campus_id: str, payload: CampusSettingsInput, db: DB, user: Actor) -> CampusSettingsOutput:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    obj = campus_settings(db, campus_id)
    apply(obj, payload.model_dump())
    obj.updated_by_user_id = user.id
    return saved(db, user, obj, 'campus.settings', campus_id)


@router.get('/campuses/{campus_id}/academic-years')
def list_years(campus_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[AcademicYearOutput]:
    require_campus(db, user, campus_id)
    return pack((serialize(y) for y in rows(db, AcademicYear) if y.campus_id == campus_id), page, page_size)


@router.post('/campuses/{campus_id}/academic-years', status_code=201)
def create_year(campus_id: str, payload: AcademicYearInput, db: DB, user: Actor) -> AcademicYearOutput:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    if payload.is_current:
        for y in db.scalars(select(AcademicYear).where(AcademicYear.campus_id == campus_id)):
            y.is_current = False
        db.flush()
    return saved(db, user, AcademicYear(campus_id=campus_id, **payload.model_dump()), 'academic_year.create', campus_id)


@router.patch('/academic-years/{year_id}')
def update_year(year_id: str, payload: AcademicYearPatch, db: DB, user: Actor) -> AcademicYearOutput:
    obj = get(db, AcademicYear, year_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN')
    values = changed(obj, payload, AcademicYearInput)
    if values['is_current']:
        for y in db.scalars(select(AcademicYear).where(AcademicYear.campus_id == obj.campus_id, AcademicYear.id != obj.id)):
            y.is_current = False
        db.flush()
    apply(obj, values)
    return saved(db, user, obj, 'academic_year.update', obj.campus_id)


@router.get('/campuses/{campus_id}/programs')
def list_programs(campus_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[ProgramOutput]:
    require_campus(db, user, campus_id)
    return pack((serialize(p) for p in rows(db, Program) if p.campus_id == campus_id), page, page_size)


@router.post('/campuses/{campus_id}/programs', status_code=201)
def create_program(campus_id: str, payload: ProgramInput, db: DB, user: Actor) -> ProgramOutput:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    return saved(db, user, Program(campus_id=campus_id, **payload.model_dump()), 'program.create', campus_id)


@router.patch('/programs/{program_id}')
def update_program(program_id: str, payload: ProgramPatch, db: DB, user: Actor) -> ProgramOutput:
    obj = get(db, Program, program_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN')
    apply(obj, changed(obj, payload, ProgramInput))
    return saved(db, user, obj, 'program.update', obj.campus_id)


@router.delete('/programs/{program_id}', status_code=204)
def archive_program(program_id: str, db: DB, user: Actor):
    obj = get(db, Program, program_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN')
    obj.status = 'ARCHIVED'
    saved(db, user, obj, 'program.archive', obj.campus_id)
    return Response(status_code=204)


@router.get('/programs/{program_id}/levels')
def list_levels(program_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[ProgramLevelOutput]:
    program = get(db, Program, program_id)
    require_campus(db, user, program.campus_id)
    levels = db.scalars(select(ProgramLevel).order_by(ProgramLevel.level_order, ProgramLevel.id).execution_options(yield_per=250))
    return pack((serialize(level) for level in levels if level.program_id == program_id), page, page_size)


@router.post('/programs/{program_id}/levels', status_code=201)
def create_level(program_id: str, payload: LevelInput, db: DB, user: Actor) -> ProgramLevelOutput:
    program = get(db, Program, program_id)
    require_role(db, user, program.campus_id, 'CAMPUS_ADMIN')
    return saved(db, user, ProgramLevel(program_id=program_id, **payload.model_dump()), 'level.create', program.campus_id)


@router.patch('/levels/{level_id}')
def update_level(level_id: str, payload: LevelPatch, db: DB, user: Actor) -> ProgramLevelOutput:
    obj = get(db, ProgramLevel, level_id)
    campus = level_campus(db, obj)
    require_role(db, user, campus, 'CAMPUS_ADMIN')
    apply(obj, changed(obj, payload, LevelInput))
    return saved(db, user, obj, 'level.update', campus)


@router.delete('/levels/{level_id}', status_code=204)
def archive_level(level_id: str, db: DB, user: Actor):
    obj = get(db, ProgramLevel, level_id)
    campus = level_campus(db, obj)
    require_role(db, user, campus, 'CAMPUS_ADMIN')
    obj.status = 'ARCHIVED'
    saved(db, user, obj, 'level.archive', campus)
    return Response(status_code=204)


@router.get('/levels/{level_id}/subjects')
def list_subjects(level_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[SubjectOutput]:
    require_campus(db, user, level_campus(db, get(db, ProgramLevel, level_id)))
    return pack((serialize(s) for s in rows(db, Subject) if s.program_level_id == level_id), page, page_size)


@router.post('/levels/{level_id}/subjects', status_code=201)
def create_subject(level_id: str, payload: SubjectInput, db: DB, user: Actor) -> SubjectOutput:
    campus = level_campus(db, get(db, ProgramLevel, level_id))
    require_role(db, user, campus, 'CAMPUS_ADMIN')
    return saved(db, user, Subject(program_level_id=level_id, **payload.model_dump()), 'subject.create', campus)


@router.patch('/subjects/{subject_id}')
def update_subject(subject_id: str, payload: SubjectPatch, db: DB, user: Actor) -> SubjectOutput:
    obj = get(db, Subject, subject_id)
    campus = level_campus(db, get(db, ProgramLevel, obj.program_level_id))
    require_role(db, user, campus, 'CAMPUS_ADMIN')
    apply(obj, changed(obj, payload, SubjectInput))
    return saved(db, user, obj, 'subject.update', campus)


@router.delete('/subjects/{subject_id}', status_code=204)
def archive_subject(subject_id: str, db: DB, user: Actor):
    obj = get(db, Subject, subject_id)
    campus = level_campus(db, get(db, ProgramLevel, obj.program_level_id))
    require_role(db, user, campus, 'CAMPUS_ADMIN')
    obj.status = 'ARCHIVED'
    saved(db, user, obj, 'subject.archive', campus)
    return Response(status_code=204)


@router.get('/campuses/{campus_id}/enrollments')
def list_enrollments(campus_id: str, db: DB, user: Actor, q: str = '', page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[EnrollmentOutput]:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    needle = q.casefold()
    items = (enrich_enrollment(db, e) for e in rows(db, Enrollment) if e.campus_id == campus_id)
    return pack((e for e in items if needle in f"{e['student_name']} {e['enrollment_number']} {e['student_email']}".casefold()), page, page_size)


@router.post('/campuses/{campus_id}/enrollments', status_code=201)
def create_enrollment(campus_id: str, payload: EnrollmentInput, db: DB, user: Actor) -> EnrollmentOutput:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN')
    student = get(db, User, payload.user_id)
    level = get(db, ProgramLevel, payload.program_level_id)
    year = get(db, AcademicYear, payload.academic_year_id)
    if not campus_member(db, student, campus_id) or level_campus(db, level) != campus_id or year.campus_id != campus_id:
        raise HTTPException(422, 'Étudiant, niveau et année doivent appartenir au même établissement actif.')
    if level.status != 'ACTIVE' or get(db, Program, level.program_id).status != 'ACTIVE' or year.status != 'ACTIVE':
        raise HTTPException(422, 'Le parcours et l’année universitaire doivent être actifs.')
    obj = Enrollment(campus_id=campus_id, created_by_user_id=user.id, **payload.model_dump())
    if obj.status == 'COMPLETED':
        obj.completed_at = utcnow()
    saved(db, user, obj, 'enrollment.create', campus_id)
    return enrich_enrollment(db, obj)


@router.get('/enrollments/{enrollment_id}')
def get_enrollment(enrollment_id: str, db: DB, user: Actor) -> EnrollmentOutput:
    obj = get(db, Enrollment, enrollment_id)
    if obj.user_id != user.id:
        require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN')
    return enrich_enrollment(db, obj)


@router.patch('/enrollments/{enrollment_id}')
def update_enrollment(enrollment_id: str, payload: EnrollmentPatch, db: DB, user: Actor) -> EnrollmentOutput:
    obj = get(db, Enrollment, enrollment_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN')
    apply(obj, payload.model_dump(exclude_unset=True))
    obj.completed_at = utcnow() if obj.status == 'COMPLETED' else obj.completed_at
    saved(db, user, obj, 'enrollment.update', obj.campus_id)
    return enrich_enrollment(db, obj)


@router.get('/students/{student_id}/enrollments')
def student_history(student_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[EnrollmentOutput]:
    if student_id != user.id and not (is_platform_admin(db, user) or any(has_role(db, user, c, 'CAMPUS_ADMIN') for c in accessible_campus_ids(db, user))):
        raise HTTPException(403, 'Accès refusé.')
    items = (enrich_enrollment(db, e) for e in rows(db, Enrollment) if e.user_id == student_id and (student_id == user.id or has_role(db, user, e.campus_id, 'CAMPUS_ADMIN')))
    return pack(items, page, page_size)


def validate_content(db, user, values, model):
    campus_id = values['campus_id']
    require_role(db, user, campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')
    if campus_id:
        campus = get(db, Campus, campus_id)
        if campus.status != 'ACTIVE':
            raise HTTPException(422, 'Cet établissement est désactivé.')
    programs = [get(db, Program, i) for i in values['program_ids']]
    levels = [get(db, ProgramLevel, i) for i in values['level_ids']]
    years = [get(db, AcademicYear, i) for i in values['year_ids']]
    if any(p.campus_id != campus_id for p in programs) or any(level_campus(db, l) != campus_id for l in levels) or any(y.campus_id != campus_id for y in years):
        raise HTTPException(422, 'Toutes les cibles doivent appartenir à l’établissement du contenu.')
    if programs and any(l.program_id not in values['program_ids'] for l in levels):
        raise HTTPException(422, 'Les niveaux ciblés doivent appartenir aux filières ciblées.')
    if model is Announcement and values['allow_comments'] and campus_id and not campus_settings(db, campus_id).allow_announcement_comments:
        raise HTTPException(422, 'Activez les commentaires officiels dans les paramètres de l’établissement.')
    if model is Document:
        asset = get(db, FileAsset, values['file_asset_id'])
        if asset.campus_id != campus_id or asset.status != 'AVAILABLE':
            raise HTTPException(422, 'Le fichier doit être disponible dans le même périmètre.')
        if values['subject_id']:
            subject = get(db, Subject, values['subject_id'])
            level = get(db, ProgramLevel, subject.program_level_id)
            if level_campus(db, level) != campus_id:
                raise HTTPException(422, 'La matière appartient à un autre établissement.')
            if values['program_ids'] and level.program_id not in values['program_ids'] or values['level_ids'] and level.id not in values['level_ids']:
                raise HTTPException(422, 'La matière doit correspondre aux filières et niveaux ciblés.')


def content_create(model, payload, db, user):
    values = payload.model_dump()
    validate_content(db, user, values, model)
    author_key = 'author_user_id' if model is Announcement else 'uploaded_by_user_id'
    obj = model(**values, **{author_key: user.id})
    db.add(obj)
    db.flush()
    if obj.status == 'PUBLISHED':
        obj.published_at = utcnow()
        notify_publication(db, obj)
    return saved(db, user, obj, f'{obj.__tablename__}.create', obj.campus_id)


def content_update(model, schema, content_id, payload, db, user):
    obj = get(db, model, content_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')
    values = changed(obj, payload, schema)
    validate_content(db, user, values, model)
    old_status = obj.status
    apply(obj, values)
    if obj.status == 'PUBLISHED':
        obj.published_at = obj.published_at or utcnow()
        db.flush()
        notify_publication(db, obj)
    return saved(db, user, obj, f'{obj.__tablename__}.update', obj.campus_id)


def content_transition(model, content_id, status, db, user):
    obj = get(db, model, content_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')
    schema = AnnouncementInput if model is Announcement else DocumentInput
    validate_content(db, user, {name: getattr(obj, name) for name in schema.model_fields}, model)
    obj.status = status
    if status == 'PUBLISHED':
        obj.published_at = obj.published_at or utcnow()
        notify_publication(db, obj)
    return saved(db, user, obj, f'{obj.__tablename__}.{status.lower()}', obj.campus_id)


def content_list(db, user, model, page, page_size, campus_id, q, manage, status, scope, program_id, level_id, year_id, category=None, subject_id=None):
    if campus_id:
        require_campus(db, user, campus_id)
    candidates = select(model).where(or_(model.campus_id.in_(accessible_campus_ids(db, user)), model.scope == 'PLATFORM'))
    if campus_id:
        candidates = candidates.where(or_(model.campus_id == campus_id, model.scope == 'PLATFORM'))
    if not manage:
        candidates = candidates.where(model.status == 'PUBLISHED')
    if status:
        candidates = candidates.where(model.status == status)
    if scope:
        candidates = candidates.where(model.scope == scope)
    ordering = [model.created_at.desc(), model.id]
    if model is Announcement:
        ordering = [model.is_pinned.desc(), model.created_at.desc(), model.id]
    needle = q.casefold()

    def visible_items():
        candidates_result = db.scalars(candidates.order_by(*ordering).execution_options(yield_per=250))
        for obj in candidates_result:
            if campus_id and obj.campus_id not in (campus_id, None):
                continue
            if manage and not can_manage_content(db, user, obj):
                continue
            if not can_view_content(db, user, obj, management=manage):
                continue
            if status and obj.status != status or scope and obj.scope != scope:
                continue
            if program_id and program_id not in obj.program_ids or level_id and level_id not in obj.level_ids or year_id and year_id not in obj.year_ids:
                continue
            if category and obj.category != category or subject_id and obj.subject_id != subject_id:
                continue
            if needle not in f'{obj.title} {getattr(obj, "summary", "") or ""} {getattr(obj, "description", "") or ""}'.casefold():
                continue
            data = serialize(obj)
            if model is Announcement:
                data['campus_name'] = get(db, Campus, obj.campus_id).name if obj.campus_id else 'Tous les établissements'
            if model is Document:
                asset = get(db, FileAsset, obj.file_asset_id)
                data.update(original_filename=asset.original_filename, mime_type=asset.mime_type, size_bytes=asset.size_bytes)
            yield data

    return pack(visible_items(), page, page_size)


@router.get('/announcements')
def list_announcements(db: DB, user: Actor, campus_id: str | None = None, q: str = '', manage: bool = False,
                       status: str | None = None, scope: str | None = None, program_id: str | None = None,
                       level_id: str | None = None, year_id: str | None = None, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[AnnouncementOutput]:
    return content_list(db, user, Announcement, page, page_size, campus_id, q, manage, status, scope, program_id, level_id, year_id)


@router.post('/announcements', status_code=201)
def create_announcement(payload: AnnouncementInput, db: DB, user: Actor) -> AnnouncementOutput:
    return content_create(Announcement, payload, db, user)


@router.get('/announcements/{announcement_id}')
def get_announcement(announcement_id: str, db: DB, user: Actor) -> AnnouncementOutput:
    obj = get(db, Announcement, announcement_id)
    if not can_view_content(db, user, obj, management=True):
        raise HTTPException(404, 'Annonce introuvable.')
    return serialize(obj)


@router.patch('/announcements/{announcement_id}')
def update_announcement(announcement_id: str, payload: AnnouncementPatch, db: DB, user: Actor) -> AnnouncementOutput:
    return content_update(Announcement, AnnouncementInput, announcement_id, payload, db, user)


@router.post('/announcements/{announcement_id}/publish')
def publish_announcement(announcement_id: str, db: DB, user: Actor) -> AnnouncementOutput:
    return content_transition(Announcement, announcement_id, 'PUBLISHED', db, user)


@router.post('/announcements/{announcement_id}/archive')
def archive_announcement(announcement_id: str, db: DB, user: Actor) -> AnnouncementOutput:
    return content_transition(Announcement, announcement_id, 'ARCHIVED', db, user)


def enriched_comment(db, comment):
    result = serialize(comment)
    author = get(db, User, comment.author_user_id)
    result['author_name'] = f'{author.first_name} {author.last_name}'
    if isinstance(comment, CommunityComment):
        parent = db.get(CommunityPost, comment.post_id)
        campus_id = parent.campus_id if parent else None
    else:
        parent = db.get(Announcement, comment.announcement_id)
        campus_id = parent.campus_id if parent else None
    if campus_id and author.avatar_url and not is_platform_admin(db, author):
        result['author_avatar_url'] = f'/campuses/{campus_id}/users/{author.id}/avatar'
    return result


@router.get('/announcements/{announcement_id}/comments')
def announcement_comments(announcement_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[AnnouncementCommentOutput]:
    obj = get(db, Announcement, announcement_id)
    if not can_view_content(db, user, obj):
        raise HTTPException(404, 'Annonce introuvable.')
    return pack((enriched_comment(db, c) for c in rows(db, AnnouncementComment) if c.announcement_id == obj.id and c.status == 'VISIBLE'), page, page_size)


@router.post('/announcements/{announcement_id}/comments', status_code=201)
def create_announcement_comment(announcement_id: str, payload: CommentInput, db: DB, user: Actor) -> AnnouncementCommentOutput:
    obj = get(db, Announcement, announcement_id)
    if not can_view_content(db, user, obj):
        raise HTTPException(404, 'Annonce introuvable.')
    if not obj.allow_comments or obj.campus_id and not campus_settings(db, obj.campus_id).allow_announcement_comments:
        raise HTTPException(403, 'Les commentaires sont désactivés.')
    if payload.parent_comment_id:
        raise HTTPException(422, 'Les commentaires officiels ne prennent pas en charge les réponses imbriquées.')
    comment = AnnouncementComment(announcement_id=obj.id, author_user_id=user.id, content=payload.content)
    db.add(comment)
    commit(db)
    return enriched_comment(db, comment)


@router.get('/documents')
def list_documents(db: DB, user: Actor, campus_id: str | None = None, q: str = '', manage: bool = False,
                   status: str | None = None, scope: str | None = None, program_id: str | None = None,
                   level_id: str | None = None, year_id: str | None = None, category: str | None = None,
                   subject_id: str | None = None, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[DocumentOutput]:
    return content_list(db, user, Document, page, page_size, campus_id, q, manage, status, scope, program_id, level_id, year_id, category, subject_id)


@router.post('/documents', status_code=201)
def create_document(payload: DocumentInput, db: DB, user: Actor) -> DocumentOutput:
    return content_create(Document, payload, db, user)


@router.get('/documents/{document_id}')
def get_document(document_id: str, db: DB, user: Actor) -> DocumentOutput:
    obj = get(db, Document, document_id)
    if not can_view_content(db, user, obj, management=True):
        raise HTTPException(404, 'Document introuvable.')
    result = serialize(obj)
    asset = get(db, FileAsset, obj.file_asset_id)
    result.update(original_filename=asset.original_filename, mime_type=asset.mime_type, size_bytes=asset.size_bytes)
    return result


@router.patch('/documents/{document_id}')
def update_document(document_id: str, payload: DocumentPatch, db: DB, user: Actor) -> DocumentOutput:
    return content_update(Document, DocumentInput, document_id, payload, db, user)


@router.post('/documents/{document_id}/publish')
def publish_document(document_id: str, db: DB, user: Actor) -> DocumentOutput:
    return content_transition(Document, document_id, 'PUBLISHED', db, user)


@router.post('/documents/{document_id}/archive')
def archive_document(document_id: str, db: DB, user: Actor) -> DocumentOutput:
    return content_transition(Document, document_id, 'ARCHIVED', db, user)


@router.post('/files/upload', status_code=201)
async def upload_file(db: DB, user: Actor, file: UploadFile = File(...), campus_id: str | None = Form(default=None)) -> FileAssetOutput:
    require_role(db, user, campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')
    maximum = settings.max_upload_size_mb
    if campus_id:
        maximum = min(maximum, campus_settings(db, campus_id).max_upload_size_mb)
    metadata = await save_upload(file, maximum)
    obj = FileAsset(campus_id=campus_id, uploaded_by_user_id=user.id, **metadata)
    try:
        return saved(db, user, obj, 'file.upload', campus_id)
    except Exception:
        file_path(metadata['storage_key']).unlink(missing_ok=True)
        raise


@router.get('/files/{file_id}/download')
def download_file(file_id: str, db: DB, user: Actor):
    asset = get(db, FileAsset, file_id)
    documents = db.scalars(select(Document).where(Document.file_asset_id == file_id))
    allowed = next((document for document in documents if can_view_content(db, user, document)), None)
    if asset.status != 'AVAILABLE' or allowed is None:
        raise HTTPException(404, 'Fichier introuvable ou non autorisé.')
    path = file_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(404, 'Le fichier est indisponible.')
    allowed.download_count += 1
    commit(db)
    return FileResponse(path, media_type=asset.mime_type, filename=asset.original_filename,
                        headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store'})


def event_visible(db, user, obj, management=False):
    if management and has_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER'):
        return True
    if obj.status not in ('PUBLISHED', 'COMPLETED'):
        return False
    if obj.campus_id and not (is_platform_admin(db, user) or campus_member(db, user, obj.campus_id)):
        return False
    return not obj.announcement_id or can_view_content(db, user, get(db, Announcement, obj.announcement_id))


def validate_event(db, user, values):
    require_role(db, user, values['campus_id'], 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')
    if values['announcement_id']:
        announcement = get(db, Announcement, values['announcement_id'])
        if announcement.campus_id != values['campus_id']:
            raise HTTPException(422, 'L’annonce et l’événement doivent appartenir au même établissement.')


@router.get('/events')
def list_events(db: DB, user: Actor, campus_id: str | None = None, manage: bool = False,
                q: str = '', page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[EventOutput]:
    if campus_id:
        require_campus(db, user, campus_id)
    events = db.scalars(select(Event).order_by(Event.starts_at, Event.id).execution_options(yield_per=250))
    needle = q.casefold()
    return pack((serialize(e) for e in events
                 if (not campus_id or e.campus_id in (campus_id, None)) and (not manage or has_role(db, user, e.campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER'))
                 and event_visible(db, user, e, manage) and needle in e.title.casefold()), page, page_size)


@router.post('/events', status_code=201)
def create_event(payload: EventInput, db: DB, user: Actor) -> EventOutput:
    values = payload.model_dump()
    validate_event(db, user, values)
    return saved(db, user, Event(created_by_user_id=user.id, **values), 'event.create', payload.campus_id)


@router.get('/events/{event_id}')
def get_event(event_id: str, db: DB, user: Actor) -> EventOutput:
    obj = get(db, Event, event_id)
    if not event_visible(db, user, obj, True):
        raise HTTPException(404, 'Événement introuvable.')
    return serialize(obj)


@router.patch('/events/{event_id}')
def update_event(event_id: str, payload: EventPatch, db: DB, user: Actor) -> EventOutput:
    obj = get(db, Event, event_id)
    require_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'CONTENT_PUBLISHER')
    values = changed(obj, payload, EventInput)
    validate_event(db, user, values)
    apply(obj, values)
    return saved(db, user, obj, 'event.update', obj.campus_id)


def post_visible(db, user, obj):
    return (is_platform_admin(db, user) or campus_member(db, user, obj.campus_id)) and (
        obj.status == 'VISIBLE' or obj.status != 'DELETED' and (obj.author_user_id == user.id or has_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'MODERATOR')))


def accessible_post(db, user, post_id):
    obj = get(db, CommunityPost, post_id)
    if not post_visible(db, user, obj):
        raise HTTPException(404, 'Publication introuvable.')
    return obj


def enriched_post(db, user, obj):
    result = serialize(obj)
    author = get(db, User, obj.author_user_id)
    result['author_name'] = f'{author.first_name} {author.last_name}'
    if author.avatar_url and not is_platform_admin(db, author):
        result['author_avatar_url'] = f'/campuses/{obj.campus_id}/users/{author.id}/avatar'
    result['comment_count'] = db.scalar(select(func.count()).select_from(CommunityComment).where(CommunityComment.post_id == obj.id, CommunityComment.status == 'VISIBLE'))
    result['reaction_count'] = db.scalar(select(func.count()).select_from(Reaction).where(Reaction.post_id == obj.id))
    result['my_reaction_id'] = db.scalar(select(Reaction.id).where(Reaction.post_id == obj.id, Reaction.user_id == user.id))
    return result


@router.get('/campuses/{campus_id}/users/{target_user_id}/avatar')
def campus_member_avatar(campus_id: str, target_user_id: str, db: DB, user: Actor):
    require_campus(db, user, campus_id)
    target = db.get(User, target_user_id)
    member = db.scalar(select(CampusMembership.id).where(
        CampusMembership.user_id == target_user_id,
        CampusMembership.campus_id == campus_id,
        CampusMembership.status == 'ACTIVE',
    ))
    if not target or not member or not target.avatar_url or is_platform_admin(db, target):
        raise HTTPException(404, 'Image introuvable.')
    key = target.avatar_url
    if key != key.rsplit('/', 1)[-1] or not key.startswith('avatar-'):
        raise HTTPException(404, 'Image introuvable.')
    path = file_path(key)
    if not path.is_file():
        raise HTTPException(404, 'Image introuvable.')
    return FileResponse(path, media_type='image/png' if path.suffix.lower() == '.png' else 'image/jpeg',
                        headers={'Cache-Control': 'private, max-age=300'})


def community_allowed(db, user, campus_id, permission):
    require_campus(db, user, campus_id)
    if not getattr(campus_settings(db, campus_id), permission):
        raise HTTPException(403, 'Cette fonctionnalité est désactivée dans cet établissement.')


@router.get('/community/posts')
def list_posts(db: DB, user: Actor, campus_id: str | None = None, q: str = '', page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[CommunityPostOutput]:
    if campus_id:
        require_campus(db, user, campus_id)
    candidates = select(CommunityPost).where(CommunityPost.campus_id.in_([campus_id] if campus_id else accessible_campus_ids(db, user)))
    return pack((enriched_post(db, user, p) for p in db.scalars(candidates.order_by(CommunityPost.created_at.desc()).execution_options(yield_per=250))
                 if (not campus_id or p.campus_id == campus_id) and post_visible(db, user, p)
                 and q.casefold() in f'{p.title or ""} {p.content}'.casefold()), page, page_size)


@router.post('/community/posts', status_code=201)
def create_post(payload: PostInput, db: DB, user: Actor) -> CommunityPostOutput:
    community_allowed(db, user, payload.campus_id, 'allow_student_posts')
    obj = CommunityPost(author_user_id=user.id, **payload.model_dump())
    db.add(obj)
    commit(db)
    return enriched_post(db, user, obj)


@router.get('/community/posts/{post_id}')
def get_post(post_id: str, db: DB, user: Actor) -> CommunityPostOutput:
    return enriched_post(db, user, accessible_post(db, user, post_id))


@router.patch('/community/posts/{post_id}')
def update_post(post_id: str, payload: PostPatch, db: DB, user: Actor) -> CommunityPostOutput:
    obj = accessible_post(db, user, post_id)
    if obj.author_user_id != user.id:
        raise HTTPException(403, 'Seul l’auteur peut modifier cette publication.')
    if obj.status != 'VISIBLE':
        raise HTTPException(409, 'Une publication modérée ne peut pas être modifiée.')
    community_allowed(db, user, obj.campus_id, 'allow_student_posts')
    values = payload.model_dump(exclude_unset=True)
    if 'content' in values and values['content'] is None:
        raise HTTPException(422, 'Le contenu ne peut pas être vide.')
    apply(obj, values)
    commit(db)
    return enriched_post(db, user, obj)


@router.delete('/community/posts/{post_id}', status_code=204)
def delete_post(post_id: str, db: DB, user: Actor):
    obj = accessible_post(db, user, post_id)
    if obj.author_user_id != user.id:
        raise HTTPException(403, 'Seul l’auteur peut retirer sa publication. Utilisez la modération pour masquer un contenu.')
    obj.status = 'DELETED'
    commit(db)
    return Response(status_code=204)


@router.get('/community/posts/{post_id}/comments')
def post_comments(post_id: str, db: DB, user: Actor, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[CommunityCommentOutput]:
    obj = accessible_post(db, user, post_id)
    moderation = has_role(db, user, obj.campus_id, 'CAMPUS_ADMIN', 'MODERATOR')
    comments = db.scalars(select(CommunityComment).order_by(CommunityComment.created_at, CommunityComment.id).execution_options(yield_per=250))
    return pack((enriched_comment(db, c) for c in comments if c.post_id == obj.id
                 and (c.status == 'VISIBLE' or c.status != 'DELETED' and (c.author_user_id == user.id or moderation))), page, page_size)


@router.post('/community/posts/{post_id}/comments', status_code=201)
def create_post_comment(post_id: str, payload: CommentInput, db: DB, user: Actor) -> CommunityCommentOutput:
    obj = accessible_post(db, user, post_id)
    community_allowed(db, user, obj.campus_id, 'allow_student_comments')
    if obj.status != 'VISIBLE':
        raise HTTPException(409, 'Les interactions sont fermées sur cette publication.')
    if payload.parent_comment_id:
        parent = get(db, CommunityComment, payload.parent_comment_id)
        if parent.post_id != obj.id or parent.status != 'VISIBLE':
            raise HTTPException(422, 'Le commentaire parent doit être visible et appartenir à la même publication.')
    comment = CommunityComment(post_id=obj.id, author_user_id=user.id, **payload.model_dump())
    db.add(comment)
    db.flush()
    if obj.author_user_id != user.id:
        author = get(db, User, obj.author_user_id)
        if campus_member(db, author, obj.campus_id):
            db.add(Notification(user_id=author.id, campus_id=obj.campus_id, event_key=f'comment:{comment.id}',
                                notification_type='COMMUNITY', title='Une réponse à votre publication',
                                message=f'{user.first_name} a commenté votre publication.', link=f'/app/community/{obj.id}'))
            preference = db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == author.id))
            if preference and preference.email_community:
                from app.services.mail import branded_email, queue_email
                url = f'{settings.frontend_url.rstrip("/")}/app/community/{obj.id}'
                queue_email(db, author.email, 'CampusPulse — Une nouvelle réponse',
                            f'{user.first_name} a répondu à votre publication. Consultez votre espace : {url}',
                            branded_email('Une réponse à votre publication', 'Une personne a réagi à votre échange.', author.first_name,
                                          [f'{user.first_name} a commenté votre publication.'], button_text='Voir la conversation', button_url=url))
    commit(db)
    return enriched_comment(db, comment)


@router.patch('/community/comments/{comment_id}')
def update_comment(comment_id: str, payload: CommentInput, db: DB, user: Actor) -> CommunityCommentOutput:
    obj = get(db, CommunityComment, comment_id)
    post = accessible_post(db, user, obj.post_id)
    if obj.author_user_id != user.id:
        raise HTTPException(403, 'Seul l’auteur peut modifier son commentaire.')
    if obj.status != 'VISIBLE' or post.status != 'VISIBLE':
        raise HTTPException(409, 'Un contenu modéré ne peut pas être modifié.')
    if payload.parent_comment_id is not None and payload.parent_comment_id != obj.parent_comment_id:
        raise HTTPException(422, 'Le commentaire parent ne peut pas être modifié.')
    obj.content = payload.content
    commit(db)
    return enriched_comment(db, obj)


@router.delete('/community/comments/{comment_id}', status_code=204)
def delete_comment(comment_id: str, db: DB, user: Actor):
    obj = get(db, CommunityComment, comment_id)
    accessible_post(db, user, obj.post_id)
    if obj.author_user_id != user.id:
        raise HTTPException(403, 'Seul l’auteur peut retirer son commentaire.')
    obj.status = 'DELETED'
    commit(db)
    return Response(status_code=204)


def community_target(db, user, payload, moderation=False):
    if payload.comment_id:
        target = get(db, CommunityComment, payload.comment_id)
        post = get(db, CommunityPost, target.post_id)
    else:
        target = get(db, CommunityPost, payload.post_id)
        post = target
    if moderation:
        require_role(db, user, post.campus_id, 'CAMPUS_ADMIN', 'MODERATOR')
    elif target.status != 'VISIBLE' or post.status != 'VISIBLE' or not post_visible(db, user, post):
        raise HTTPException(404, 'Contenu introuvable.')
    return target, post


@router.post('/community/reactions', status_code=201)
def react(payload: ReactionInput, db: DB, user: Actor) -> ReactionOutput:
    target, post = community_target(db, user, payload)
    community_allowed(db, user, post.campus_id, 'allow_student_reactions')
    obj = db.scalar(select(Reaction).where(Reaction.user_id == user.id, Reaction.post_id == payload.post_id,
                                         Reaction.comment_id == payload.comment_id))
    if not obj:
        obj = Reaction(user_id=user.id, **payload.model_dump())
        db.add(obj)
    else:
        obj.reaction_type = payload.reaction_type
    commit(db)
    return serialize(obj)


@router.delete('/community/reactions/{reaction_id}', status_code=204)
def remove_reaction(reaction_id: str, db: DB, user: Actor):
    obj = get(db, Reaction, reaction_id)
    if obj.user_id != user.id:
        raise HTTPException(403, 'Cette réaction ne vous appartient pas.')
    db.delete(obj)
    commit(db)
    return Response(status_code=204)


@router.post('/reports', status_code=201)
def create_report(payload: ReportInput, db: DB, user: Actor) -> ReportOutput:
    target, post = community_target(db, user, payload)
    existing = db.scalar(select(Report).where(Report.reporter_user_id == user.id, Report.post_id == payload.post_id,
                        Report.comment_id == payload.comment_id, Report.status == 'OPEN'))
    if existing:
        raise HTTPException(409, 'Vous avez déjà signalé ce contenu ; votre signalement est en cours de traitement.')
    obj = Report(campus_id=post.campus_id, reporter_user_id=user.id, **payload.model_dump())
    db.add(obj)
    commit(db)
    return serialize(obj)


@router.get('/moderation/reports')
def list_reports(db: DB, user: Actor, campus_id: str | None = None, status: str | None = 'OPEN',
                 page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[ReportOutput]:
    if campus_id:
        require_role(db, user, campus_id, 'CAMPUS_ADMIN', 'MODERATOR')
    allowed = [c for c in accessible_campus_ids(db, user) if has_role(db, user, c, 'CAMPUS_ADMIN', 'MODERATOR')]
    if not allowed and not is_platform_admin(db, user):
        raise HTTPException(403, 'Accès à la modération refusé.')
    result = []
    for obj in rows(db, Report):
        if obj.campus_id not in allowed or campus_id and obj.campus_id != campus_id or status and obj.status != status:
            continue
        target = get(db, CommunityComment, obj.comment_id) if obj.comment_id else get(db, CommunityPost, obj.post_id)
        post = get(db, CommunityPost, target.post_id) if obj.comment_id else target
        reporter = get(db, User, obj.reporter_user_id)
        result.append({**serialize(obj), 'post_title': post.title, 'content': target.content,
                       'reporter_name': f'{reporter.first_name} {reporter.last_name}'})
    return pack(result, page, page_size)


def moderate(db, user, target, post, action, reason, report_id=None):
    if target.status == 'DELETED' and action != 'NONE':
        raise HTTPException(409, 'Un contenu retiré par son auteur ne peut plus être modéré ou restauré.')
    if action in ('HIDE', 'RESTORE'):
        target.status = 'HIDDEN' if action == 'HIDE' else 'VISIBLE'
    record = ModerationAction(campus_id=post.campus_id, moderator_user_id=user.id, report_id=report_id,
                              post_id=target.id if isinstance(target, CommunityPost) else None,
                              comment_id=target.id if isinstance(target, CommunityComment) else None,
                              action=action, reason=reason)
    db.add(record)
    db.flush()
    audit(db, user, f'moderation.{action.lower()}', target.__tablename__, target.id, post.campus_id,
          {'reason': reason, 'report_id': report_id})
    return record


@router.patch('/moderation/reports/{report_id}')
def resolve_report(report_id: str, payload: ModerationInput, db: DB, user: Actor) -> ReportOutput:
    report = get(db, Report, report_id)
    require_role(db, user, report.campus_id, 'CAMPUS_ADMIN', 'MODERATOR')
    if report.status != 'OPEN':
        raise HTTPException(409, 'Ce signalement a déjà été traité.')
    target, post = community_target(db, user, report, moderation=True)
    moderate(db, user, target, post, payload.action, payload.reason, report.id)
    report.status = payload.status
    report.resolved_at = utcnow()
    report.resolved_by_user_id = user.id
    commit(db)
    return serialize(report)


@router.post('/moderation/actions', status_code=201)
def direct_moderation(payload: DirectModerationInput, db: DB, user: Actor) -> ModerationActionOutput:
    target, post = community_target(db, user, payload, moderation=True)
    record = moderate(db, user, target, post, payload.action, payload.reason)
    commit(db)
    return serialize(record)


def notification_visible(db, user, notification):
    if notification.user_id != user.id:
        return False
    if notification.campus_id and notification.campus_id not in accessible_campus_ids(db, user):
        return False
    parts = notification.event_key.split(':')
    if len(parts) >= 2 and parts[0] in ('announcements', 'documents'):
        model = Announcement if parts[0] == 'announcements' else Document
        target = db.get(model, parts[1])
        return bool(target and can_view_content(db, user, target))
    if len(parts) >= 2 and parts[0] == 'comment':
        comment = db.get(CommunityComment, parts[1])
        post = db.get(CommunityPost, comment.post_id) if comment else None
        return bool(comment and comment.status == 'VISIBLE' and post and post_visible(db, user, post))
    return True


@router.get('/notifications')
def notifications(db: DB, user: Actor, unread: bool = False, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[NotificationOutput]:
    candidates = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
    if unread:
        candidates = candidates.where(Notification.read_at.is_(None))
    return pack((serialize(n) for n in db.scalars(candidates.execution_options(yield_per=250)) if notification_visible(db, user, n)), page, page_size)


@router.patch('/notifications/{notification_id}/read')
def read_notification(notification_id: str, db: DB, user: Actor) -> NotificationOutput:
    obj = get(db, Notification, notification_id)
    if not notification_visible(db, user, obj):
        raise HTTPException(404, 'Notification introuvable.')
    obj.read_at = obj.read_at or utcnow()
    commit(db)
    return serialize(obj)


@router.post('/notifications/read-all')
def read_all_notifications(db: DB, user: Actor) -> MessageOutput:
    for obj in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))):
        obj.read_at = utcnow()
    commit(db)
    return {'message': 'Toutes les notifications ont été marquées comme lues.'}


@router.get('/dashboard/summary')
def dashboard_summary(db: DB, user: Actor, campus_id: str | None = None) -> DashboardOutput:
    if campus_id:
        require_campus(db, user, campus_id)
    allowed = [campus_id] if campus_id else accessible_campus_ids(db, user)
    managed = [c for c in allowed if has_role(db, user, c, 'CAMPUS_ADMIN')]
    moderated = [c for c in allowed if has_role(db, user, c, 'CAMPUS_ADMIN', 'MODERATOR')]
    students = db.scalar(select(func.count(func.distinct(CampusMembership.user_id))).where(
        CampusMembership.campus_id.in_(managed), CampusMembership.status == 'ACTIVE',
        CampusMembership.membership_type == 'STUDENT')) or 0
    announcement_count = sum(1 for a in rows(db, Announcement) if a.campus_id in [*allowed, None] and can_view_content(db, user, a))
    document_count = sum(1 for d in rows(db, Document) if d.campus_id in [*allowed, None] and can_view_content(db, user, d))
    return {'campuses': len(allowed), 'students': students, 'announcements': announcement_count, 'documents': document_count,
            'events': sum(e.campus_id in [*allowed, None] and event_visible(db, user, e) for e in rows(db, Event)),
            'posts': sum(p.campus_id in allowed and post_visible(db, user, p) for p in rows(db, CommunityPost)),
            'unread_notifications': sum(notification_visible(db, user, n) and n.campus_id in [*allowed, None] for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)))),
            'pending_reports': db.scalar(select(func.count()).select_from(Report).where(Report.campus_id.in_(moderated), Report.status == 'OPEN')),
            'enrollments': sum(e.campus_id in allowed and (e.user_id == user.id or e.campus_id in managed) for e in rows(db, Enrollment))}


@router.get('/dashboard/activity')
def dashboard_activity(db: DB, user: Actor, campus_id: str | None = None, page: Page = 1, page_size: PageSize = 20) -> CollectionOutput[ActivityOutput]:
    if campus_id:
        require_campus(db, user, campus_id)
    allowed = [campus_id] if campus_id else accessible_campus_ids(db, user)
    activity = []
    for model, type_, path in [(Announcement, 'ANNOUNCEMENT', 'announcements'), (Document, 'DOCUMENT', 'documents'), (CommunityPost, 'COMMUNITY', 'community')]:
        for item in rows(db, model):
            visible = post_visible(db, user, item) if model is CommunityPost else can_view_content(db, user, item)
            if visible and item.campus_id in [*allowed, None]:
                activity.append({'id': item.id, 'type': type_, 'title': item.title or item.content[:100],
                                 'created_at': item.created_at, 'link': f'/app/{path}/{item.id}', 'campus_id': item.campus_id})
    activity.sort(key=lambda a: a['created_at'], reverse=True)
    return pack(activity, page, page_size)
