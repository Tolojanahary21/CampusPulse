from datetime import date

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import AcademicYear, AuditLog, CampusMembership, Enrollment, Notification, RoleAssignment


def create_announcement(client, data, **changes):
    body = {'campus_id':data['campus_a'],'title':'Information officielle','content':'Le calendrier pédagogique est disponible.','scope':'CAMPUS','status':'DRAFT', **changes}
    result = client.post('/api/v1/announcements', json=body)
    assert result.status_code in (200,201), result.text
    return result.json()


def test_tenant_isolation_for_admin_and_student(client, login, data):
    login('admin')
    response = client.post(f"/api/v1/campuses/{data['campus_b']}/programs", json={'name':'Intrusion','code':'X'})
    assert response.status_code in (403,404)
    announcement = create_announcement(client, data, status='PUBLISHED')
    login('outsider')
    assert client.get(f"/api/v1/announcements/{announcement['id']}").status_code in (403,404)
    assert not client.get('/api/v1/announcements').json()['items']
    login('student')
    assert client.get('/api/v1/platform/users').status_code == 403
    assert client.post('/api/v1/announcements', json={'campus_id':data['campus_a'],'title':'Fake','content':'Not official'}).status_code == 403


def test_drafts_targeting_and_notification_recipients(client, login, data):
    login('admin')
    announcement = create_announcement(client, data, scope='TARGETED', program_ids=[data['program_a']], level_ids=[data['level_a']], year_ids=[data['year_a']])
    login('student')
    assert client.get(f"/api/v1/announcements/{announcement['id']}").status_code in (403,404)
    login('admin')
    assert client.post(f"/api/v1/announcements/{announcement['id']}/publish").status_code == 200
    login('student')
    assert client.get(f"/api/v1/announcements/{announcement['id']}").status_code == 200
    with SessionLocal() as db:
        recipients = {n.user_id for n in db.scalars(select(Notification))}
        assert data['student'] in recipients
        assert data['outsider'] not in recipients
    login('admin')
    wrong_level = create_announcement(client, data, status='PUBLISHED', scope='TARGETED', level_ids=[data['level_a2']])
    login('student')
    assert client.get(f"/api/v1/announcements/{wrong_level['id']}").status_code in (403,404)


def test_cross_campus_targets_and_enrollments_rejected(client, login, data):
    login('admin')
    result = client.post('/api/v1/announcements', json={'campus_id':data['campus_a'],'title':'Wrong target','content':'Body','scope':'TARGETED','program_ids':[data['program_b']]})
    assert result.status_code in (403,422)
    result = client.post(f"/api/v1/campuses/{data['campus_a']}/enrollments", json={'user_id':data['student'],'program_level_id':data['level_a'],'academic_year_id':data['year_b'],'enrollment_number':'BAD-1'})
    assert result.status_code in (403,422)
    result = client.post(f"/api/v1/campuses/{data['campus_a']}/enrollments", json={'user_id':data['outsider'],'program_level_id':data['level_a'],'academic_year_id':data['year_a'],'enrollment_number':'BAD-2'})
    assert result.status_code in (403,422)


def test_enrollment_history_is_preserved(client, login, data):
    login('admin')
    year = client.post(f"/api/v1/campuses/{data['campus_a']}/academic-years", json={'name':'2027-2028','starts_on':'2027-09-01','ends_on':'2028-08-31','is_current':False})
    assert year.status_code in (200,201), year.text
    result = client.post(f"/api/v1/campuses/{data['campus_a']}/enrollments", json={'user_id':data['student'],'program_level_id':data['level_a2'],'academic_year_id':year.json()['id'],'enrollment_number':'A-002'})
    assert result.status_code in (200,201), result.text
    login('student')
    history = client.get(f"/api/v1/students/{data['student']}/enrollments")
    assert history.status_code == 200
    assert history.json()['total'] == 2
    assert client.get(f"/api/v1/students/{data['outsider']}/enrollments").status_code in (403,404)


def test_private_download_revalidates_permissions(client, login, data):
    login('admin')
    uploaded = client.post('/api/v1/files/upload', data={'campus_id':data['campus_a']}, files={'file':('cours.txt', b'Cours confidentiel', 'text/plain')})
    assert uploaded.status_code in (200,201), uploaded.text
    asset = uploaded.json()
    assert 'storage_key' not in asset
    assert client.get(f"/api/v1/files/{asset['id']}/download").status_code in (403,404)
    document = client.post('/api/v1/documents', json={'campus_id':data['campus_a'],'file_asset_id':asset['id'],'title':'Cours L1','scope':'TARGETED','level_ids':[data['level_a']],'status':'PUBLISHED','category':'COURSE'})
    assert document.status_code in (200,201), document.text
    login('student')
    download = client.get(f"/api/v1/files/{asset['id']}/download")
    assert download.status_code == 200
    assert download.content == b'Cours confidentiel'
    assert 'attachment' in download.headers['content-disposition']
    login('outsider')
    assert client.get(f"/api/v1/files/{asset['id']}/download").status_code in (403,404)
    login('student')
    with SessionLocal() as db:
        membership = db.scalar(select(CampusMembership).where(CampusMembership.user_id == data['student']))
        membership.status = 'SUSPENDED'
        db.commit()
    assert client.get(f"/api/v1/files/{asset['id']}/download").status_code in (403,404)


def test_malicious_upload_and_foreign_file_rejected(client, login, data):
    login('admin')
    assert client.post('/api/v1/files/upload', data={'campus_id':data['campus_a']}, files={'file':('pretend.pdf', b'<script>alert(1)</script>','application/pdf')}).status_code == 422
    assert client.post('/api/v1/files/upload', data={'campus_id':data['campus_a']}, files={'file':('virus.exe', b'MZ','application/octet-stream')}).status_code == 422
    uploaded = client.post('/api/v1/files/upload', data={'campus_id':data['campus_a']}, files={'file':('course.txt',b'Course text','text/plain')}).json()
    login('admin_b')
    response = client.post('/api/v1/documents', json={'campus_id':data['campus_b'],'file_asset_id':uploaded['id'],'title':'Stolen','status':'PUBLISHED'})
    assert response.status_code in (403,422)


def test_community_moderation_is_scoped_and_audited(client, login, data):
    login('student')
    post = client.post('/api/v1/community/posts', json={'campus_id':data['campus_a'],'title':'Question de cours','content':'Qui révise les algorithmes ?'})
    assert post.status_code in (200,201), post.text
    post_id = post.json()['id']
    assert client.post(f'/api/v1/community/posts/{post_id}/comments',json={'content':'Je participe.'}).status_code in (200,201)
    assert client.post('/api/v1/community/reactions',json={'post_id':post_id,'reaction_type':'LIKE'}).status_code in (200,201)
    report = client.post('/api/v1/reports',json={'post_id':post_id,'reason':'SPAM','description':'Vérification demandée'})
    assert report.status_code in (200,201), report.text
    report_id = report.json()['id']
    login('admin_b')
    assert client.patch(f'/api/v1/moderation/reports/{report_id}',json={'status':'RESOLVED','action':'HIDE','reason':'Motif de modération'}).status_code in (403,404)
    login('admin')
    result = client.patch(f'/api/v1/moderation/reports/{report_id}',json={'status':'RESOLVED','action':'HIDE','reason':'Contenu masqué après examen'})
    assert result.status_code == 200, result.text
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.actor_user_id == data['admin'])) is not None


def test_notification_cannot_be_marked_read_by_another_user(client, login, data):
    login('admin')
    create_announcement(client,data,status='PUBLISHED')
    with SessionLocal() as db:
        notification = db.scalar(select(Notification).where(Notification.user_id == data['student']))
        notification_id = notification.id
    login('outsider')
    assert client.patch(f'/api/v1/notifications/{notification_id}/read').status_code in (403,404)


def test_role_revocation_takes_effect_without_relogin(client, login, data):
    login('admin')
    with SessionLocal() as db:
        role = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == data['admin']))
        from app.core.security import utcnow
        role.revoked_at = utcnow()
        db.commit()
    assert client.post(f"/api/v1/campuses/{data['campus_a']}/programs",json={'name':'No permission','code':'DENIED'}).status_code == 403
