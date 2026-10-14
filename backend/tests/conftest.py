import os
from datetime import date

# Tests never connect to the configured development/production database or SMTP.
os.environ.update(APP_ENV='test', DATABASE_URL='sqlite+pysqlite:///:memory:', SMTP_ENABLED='false', SECRET_KEY='test-secret-for-isolated-automated-tests-only', COOKIE_SECURE='false', CORS_ORIGINS='["http://localhost:3000"]', TRUSTED_HOSTS='["testserver","localhost","127.0.0.1"]')

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import AuthRateLimit
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import AcademicYear, Campus, CampusMembership, CampusSettings, Enrollment, Program, ProgramLevel, RoleAssignment, Subject, User
from app.services.mail import MailOutbox

PASSWORD = 'CampusPulse-test-2026!'


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'storage_path', tmp_path / 'storage')
    monkeypatch.setattr(settings, 'smtp_enabled', False)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def data():
    with SessionLocal() as db:
        ca = Campus(name='Université A', code='A', slug='universite-a', country='Madagascar')
        cb = Campus(name='Université B', code='B', slug='universite-b', country='Madagascar')
        db.add_all([ca, cb]); db.flush()
        db.add_all([CampusSettings(campus_id=ca.id), CampusSettings(campus_id=cb.id)])
        users = {}
        for key, role, campus in [('platform', 'PLATFORM_ADMIN', None), ('admin', 'CAMPUS_ADMIN', ca), ('student', 'STUDENT', ca), ('outsider', 'STUDENT', cb), ('admin_b', 'CAMPUS_ADMIN', cb)]:
            user = User(email=f'{key}@example.com', first_name=key.capitalize(), last_name='Test', password_hash=hash_password(PASSWORD))
            db.add(user); db.flush()
            db.add(RoleAssignment(user_id=user.id, role=role, campus_id=campus.id if campus else None))
            if campus:
                db.add(CampusMembership(user_id=user.id, campus_id=campus.id, membership_type='STUDENT' if role == 'STUDENT' else 'STAFF'))
            users[key] = user.id
        pa = Program(campus_id=ca.id, code='INFO', name='Informatique')
        pb = Program(campus_id=cb.id, code='ECO', name='Économie')
        ya = AcademicYear(campus_id=ca.id, name='2026-2027', starts_on=date(2026, 9, 1), ends_on=date(2027, 8, 31), is_current=True)
        yb = AcademicYear(campus_id=cb.id, name='2026-2027', starts_on=date(2026, 9, 1), ends_on=date(2027, 8, 31), is_current=True)
        db.add_all([pa,pb,ya,yb]); db.flush()
        la = ProgramLevel(program_id=pa.id, name='Licence 1', code='L1', level_order=1)
        la2 = ProgramLevel(program_id=pa.id, name='Licence 2', code='L2', level_order=2)
        lb = ProgramLevel(program_id=pb.id, name='Licence 1', code='L1', level_order=1)
        db.add_all([la,la2,lb]); db.flush()
        sa = Subject(program_level_id=la.id, code='ALGO', name='Algorithmique')
        sb = Subject(program_level_id=lb.id, code='MACRO', name='Macroéconomie')
        enrollment = Enrollment(user_id=users['student'], campus_id=ca.id, program_level_id=la.id, academic_year_id=ya.id, enrollment_number='A-001', status='ACTIVE')
        db.add_all([sa,sb,enrollment]); db.commit()
        return {**users, 'campus_a': ca.id, 'campus_b': cb.id, 'program_a': pa.id, 'program_b': pb.id, 'level_a': la.id, 'level_a2': la2.id, 'level_b': lb.id, 'year_a': ya.id, 'year_b': yb.id, 'subject_a': sa.id, 'subject_b': sb.id, 'enrollment': enrollment.id}


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def login(client, data):
    def do_login(kind='student'):
        response = client.post('/api/v1/auth/login', json={'email': f'{kind}@example.com', 'password': PASSWORD})
        assert response.status_code == 200, response.text
        client.headers['X-CSRF-Token'] = client.cookies.get('campuspulse_csrf')
        return response.json()
    return do_login
