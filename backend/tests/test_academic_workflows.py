from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import utcnow
from app.db.session import SessionLocal
from app.models import AcademicYear, Announcement, Enrollment, Notification
from app.services.notifications import process_due_announcements
from tests.test_domains import create_announcement


def test_target_dimensions_must_match_one_enrollment(client, login, data):
    with SessionLocal() as db:
        previous = AcademicYear(campus_id=data['campus_a'],name='2025-2026',starts_on=date(2025,9,1),ends_on=date(2026,8,31))
        db.add(previous); db.flush()
        db.add(Enrollment(user_id=data['student'],campus_id=data['campus_a'],program_level_id=data['level_a2'],academic_year_id=previous.id,enrollment_number='PREVIOUS',status='ACTIVE'))
        db.commit()
    login('admin')
    item = create_announcement(client,data,status='PUBLISHED',scope='TARGETED',level_ids=[data['level_a2']],year_ids=[data['year_a']])
    login('student')
    assert client.get(f"/api/v1/announcements/{item['id']}").status_code in (403,404)


def test_historical_enrollment_grants_documents_but_not_new_targeted_announcements(client, login, data):
    with SessionLocal() as db:
        db.get(Enrollment,data['enrollment']).status = 'COMPLETED'
        db.commit()
    login('admin')
    announcement = create_announcement(client,data,status='PUBLISHED',scope='TARGETED',level_ids=[data['level_a']])
    upload = client.post('/api/v1/files/upload',data={'campus_id':data['campus_a']},files={'file':('historique.txt',b'Ancien cours','text/plain')}).json()
    document = client.post('/api/v1/documents',json={'campus_id':data['campus_a'],'title':'Ressource historique','file_asset_id':upload['id'],'scope':'TARGETED','level_ids':[data['level_a']],'status':'PUBLISHED'})
    assert document.status_code == 201
    login('student')
    assert client.get(f"/api/v1/announcements/{announcement['id']}").status_code in (403,404)
    assert client.get(f"/api/v1/documents/{document.json()['id']}").status_code == 200
    assert client.get(f"/api/v1/files/{upload['id']}/download").status_code == 200


def test_event_linked_to_targeted_announcement_inherits_visibility(client, login, data):
    login('admin')
    announcement = create_announcement(client,data,status='PUBLISHED',scope='TARGETED',level_ids=[data['level_a2']])
    event = client.post('/api/v1/events',json={'campus_id':data['campus_a'],'announcement_id':announcement['id'],'title':'Atelier réservé L2','description':'Préparation de projet L2','starts_at':'2027-01-01T09:00:00Z','ends_at':'2027-01-01T10:00:00Z','status':'PUBLISHED'})
    assert event.status_code == 201, event.text
    login('student')
    assert client.get(f"/api/v1/events/{event.json()['id']}").status_code in (403,404)
    assert client.get('/api/v1/events').json()['total'] == 0


def test_scheduled_announcement_notifies_only_when_due(client, login, data):
    login('admin')
    future = utcnow() + timedelta(days=1)
    announcement = create_announcement(client,data,status='PUBLISHED',starts_at=future.isoformat(),ends_at=(future+timedelta(days=1)).isoformat())
    with SessionLocal() as db:
        assert process_due_announcements(db)['announcements'] == 0
        assert db.scalar(select(Notification).where(Notification.user_id==data['student'])) is None
        db.get(Announcement,announcement['id']).starts_at = utcnow() - timedelta(minutes=1)
        db.commit()
        assert process_due_announcements(db)['announcements'] == 1
        db.commit()
        assert db.scalar(select(Notification).where(Notification.user_id==data['student'])) is not None
        assert process_due_announcements(db)['announcements'] == 0


def test_official_comments_require_campus_and_announcement_opt_in(client, login, data):
    login('admin')
    item = create_announcement(client,data,status='PUBLISHED')
    login('student')
    assert client.post(f"/api/v1/announcements/{item['id']}/comments",json={'content':'Un commentaire'}).status_code == 403
    login('admin')
    assert client.patch(f"/api/v1/campuses/{data['campus_a']}/settings",json={'allow_announcement_comments':True}).status_code == 200
    assert client.patch(f"/api/v1/announcements/{item['id']}",json={'allow_comments':True}).status_code == 200
    login('student')
    assert client.post(f"/api/v1/announcements/{item['id']}/comments",json={'content':'Merci pour cette information.'}).status_code == 201


def test_platform_campus_lifecycle_and_scoped_roles(client, login, data):
    login('platform')
    campus = client.post('/api/v1/platform/campuses',json={'name':'Nouveau campus','code':'NEW','slug':'nouveau-campus'})
    assert campus.status_code == 201
    campus_id = campus.json()['id']
    assigned = client.post(f'/api/v1/platform/campuses/{campus_id}/admins',json={'user_id':data['student'],'role':'CAMPUS_ADMIN'})
    assert assigned.status_code == 201
    login('student')
    assert client.post(f'/api/v1/campuses/{campus_id}/programs',json={'code':'NEW','name':'Nouveau programme'}).status_code == 201
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/programs",json={'code':'NO','name':'Not allowed'}).status_code == 403
    login('platform')
    assert client.delete(f"/api/v1/roles/{assigned.json()['id']}").status_code == 204
    assert client.patch(f'/api/v1/platform/campuses/{campus_id}',json={'status':'ARCHIVED'}).status_code == 200
    audits = client.get('/api/v1/platform/audit-logs').json()['items']
    assert any(a['action']=='role.grant' for a in audits)


def test_pagination_and_openapi_are_available(client, login):
    login('platform')
    result = client.get('/api/v1/platform/users?page_size=2&page=2')
    assert result.status_code == 200 and len(result.json()['items']) == 2
    assert result.json()['total'] == 5
    assert client.get('/api/v1/platform/users?page_size=100000').status_code == 422
    schema = client.get('/openapi.json')
    assert schema.status_code == 200
    assert '/api/v1/announcements' in schema.json()['paths']
