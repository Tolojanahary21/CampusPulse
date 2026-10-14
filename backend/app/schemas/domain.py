from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, create_model, model_validator, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class CampusInput(Input):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=50, pattern=r'^[A-Za-z0-9_-]+$')
    slug: str = Field(min_length=2, max_length=200, pattern=r'^[a-z0-9-]+$')
    description: str | None = Field(default=None, max_length=10000)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=100)
    country: str = Field(default='Madagascar', min_length=2, max_length=100)
    website_url: str | None = Field(default=None, max_length=1000, pattern=r'^https?://')
    status: Literal['ACTIVE', 'SUSPENDED', 'ARCHIVED'] = 'ACTIVE'


class RoleInput(Input):
    user_id: str
    role: Literal['CAMPUS_ADMIN', 'CONTENT_PUBLISHER', 'MODERATOR', 'STUDENT'] = 'CAMPUS_ADMIN'
    expires_at: datetime | None = None


class UserStatusInput(Input):
    status: Literal['ACTIVE', 'SUSPENDED', 'DISABLED']


class AcademicYearInput(Input):
    name: str = Field(min_length=3, max_length=50)
    starts_on: date
    ends_on: date
    is_current: bool = False
    status: Literal['ACTIVE', 'ARCHIVED'] = 'ACTIVE'

    @model_validator(mode='after')
    def dates(self):
        if self.starts_on >= self.ends_on:
            raise ValueError('La date de fin doit suivre la date de début.')
        return self


class ProgramInput(Input):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal['ACTIVE', 'ARCHIVED'] = 'ACTIVE'


class LevelInput(ProgramInput):
    level_order: int = Field(ge=1, le=20)


class SubjectInput(ProgramInput):
    credits: float | None = Field(default=None, ge=0, le=100)
    semester: int | None = Field(default=None, ge=1, le=20)


class EnrollmentInput(Input):
    user_id: str
    program_level_id: str
    academic_year_id: str
    enrollment_number: str = Field(min_length=1, max_length=80)
    status: Literal['PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED', 'SUSPENDED'] = 'ACTIVE'
    notes: str | None = Field(default=None, max_length=2000)


class EnrollmentPatch(Input):
    status: Literal['PENDING', 'ACTIVE', 'COMPLETED', 'CANCELLED', 'SUSPENDED']
    notes: str | None = Field(default=None, max_length=2000)


class TargetedInput(Input):
    campus_id: str | None = None
    title: str = Field(min_length=3, max_length=250)
    scope: Literal['CAMPUS', 'TARGETED', 'PLATFORM'] = 'CAMPUS'
    status: Literal['DRAFT', 'PUBLISHED', 'ARCHIVED'] = 'DRAFT'
    program_ids: list[str] = Field(default_factory=list, max_length=100)
    level_ids: list[str] = Field(default_factory=list, max_length=100)
    year_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def scope_check(self):
        if self.scope == 'PLATFORM' and self.campus_id is not None:
            raise ValueError('Un contenu plateforme ne doit pas être rattaché à un établissement.')
        if self.scope != 'PLATFORM' and not self.campus_id:
            raise ValueError('Un établissement est requis.')
        targets = self.program_ids or self.level_ids or self.year_ids
        if self.scope != 'TARGETED' and targets:
            raise ValueError('Les destinataires nécessitent le périmètre TARGETED.')
        if self.scope == 'TARGETED' and not targets:
            raise ValueError('Ajoutez au moins une cible pour un contenu ciblé.')
        for field in ('program_ids', 'level_ids', 'year_ids'):
            if len(getattr(self, field)) != len(set(getattr(self, field))):
                raise ValueError('Les cibles doivent être uniques.')
        return self


class AnnouncementInput(TargetedInput):
    content: str = Field(min_length=3, max_length=100000)
    summary: str | None = Field(default=None, max_length=500)
    announcement_type: Literal['GENERAL', 'ADMINISTRATIVE', 'ACADEMIC', 'EVENT', 'URGENT'] = 'GENERAL'
    is_pinned: bool = False
    allow_comments: bool = False
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def utc(cls, value):
        if value and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @model_validator(mode='after')
    def dates(self):
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValueError('Période de visibilité invalide.')
        return self


class DocumentInput(TargetedInput):
    description: str | None = Field(default=None, max_length=10000)
    file_asset_id: str
    subject_id: str | None = None
    category: Literal['COURSE', 'EXERCISE', 'SOLUTION', 'EXAM', 'SUMMARY', 'OTHER'] = 'COURSE'


class EventInput(Input):
    campus_id: str | None = None
    announcement_id: str | None = None
    title: str = Field(min_length=3, max_length=250)
    description: str = Field(min_length=3, max_length=20000)
    location: str | None = Field(default=None, max_length=250)
    starts_at: datetime
    ends_at: datetime
    registration_url: str | None = Field(default=None, pattern=r'^https?://', max_length=1000)
    status: Literal['DRAFT', 'PUBLISHED', 'CANCELLED', 'COMPLETED'] = 'DRAFT'

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def utc(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    @model_validator(mode='after')
    def dates(self):
        if self.starts_at >= self.ends_at:
            raise ValueError('La fin doit suivre le début de l’événement.')
        return self


class CommentInput(Input):
    content: str = Field(min_length=1, max_length=10000)
    parent_comment_id: str | None = None


class PostInput(Input):
    campus_id: str
    title: str | None = Field(default=None, max_length=250)
    content: str = Field(min_length=1, max_length=20000)
    post_type: Literal['QUESTION', 'DISCUSSION', 'RESOURCE', 'ANNOUNCEMENT', 'OTHER'] = 'DISCUSSION'


class PostPatch(Input):
    title: str | None = Field(default=None, max_length=250)
    content: str | None = Field(default=None, min_length=1, max_length=20000)


class TargetInput(Input):
    post_id: str | None = None
    comment_id: str | None = None

    @model_validator(mode='after')
    def target(self):
        if bool(self.post_id) == bool(self.comment_id):
            raise ValueError('Sélectionnez exactement une publication ou un commentaire.')
        return self


class ReactionInput(TargetInput):
    reaction_type: Literal['LIKE'] = 'LIKE'


class ReportInput(TargetInput):
    reason: Literal['SPAM', 'HARASSMENT', 'INAPPROPRIATE', 'MISINFORMATION', 'OTHER']
    description: str | None = Field(default=None, max_length=3000)


class ModerationInput(Input):
    status: Literal['RESOLVED', 'DISMISSED'] = 'RESOLVED'
    action: Literal['HIDE', 'RESTORE', 'NONE'] = 'NONE'
    reason: str = Field(min_length=3, max_length=3000)


class DirectModerationInput(TargetInput):
    action: Literal['HIDE', 'RESTORE']
    reason: str = Field(min_length=3, max_length=3000)


class CampusSettingsInput(Input):
    allow_announcement_comments: bool = False
    allow_student_posts: bool = True
    allow_student_comments: bool = True
    allow_student_reactions: bool = True
    max_upload_size_mb: int = Field(default=20, ge=1, le=100)


class PlatformSettingsInput(Input):
    platform_name: str = Field(default='CampusPulse', min_length=2, max_length=100)
    support_email: EmailStr | None = None
    maintenance_message: str | None = Field(default=None, max_length=1000)


def partial(schema):
    # Patch payloads retain field validation; merged payloads run full model validation.
    return create_model(schema.__name__.replace('Input', 'Patch'), __base__=Input,
                        **{name: (field.annotation | None, None) for name, field in schema.model_fields.items()})


CampusPatch = partial(CampusInput)
AcademicYearPatch = partial(AcademicYearInput)
ProgramPatch = partial(ProgramInput)
LevelPatch = partial(LevelInput)
SubjectPatch = partial(SubjectInput)
AnnouncementPatch = partial(AnnouncementInput)
DocumentPatch = partial(DocumentInput)
EventPatch = partial(EventInput)
