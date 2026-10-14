"""Explicit, idempotent development demonstration; never runs on application startup."""
import hashlib
import os
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import *
from app.services.storage import file_path


def seed():
    if settings.app_env == 'production':
        raise SystemExit('Les données de démonstration sont interdites en production. Utilisez app.create_admin.')
    password = os.environ.get('DEMO_PASSWORD', '')
    if not password:
        # Loading backend/.env keeps the command consistent with application configuration.
        from dotenv import dotenv_values
        password = dotenv_values(Path(__file__).resolve().parents[1] / '.env').get('DEMO_PASSWORD') or ''
    if len(password) < 12:
        raise SystemExit('Définissez DEMO_PASSWORD avec au moins 12 caractères avant de lancer la démonstration.')
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == 'admin@campuspulse.test')):
            print('Démonstration déjà installée ; aucun compte ni mot de passe modifié.')
            return
        created_files = []
        try:
            _populate(db, password, created_files)
            db.commit()
        except Exception:
            db.rollback()
            for path in created_files:
                path.unlink(missing_ok=True)
            raise
    print('Démonstration installée : 2 établissements, 3 profils et bibliothèque privée.')
    print('Comptes : admin@campuspulse.test, responsable@campuspulse.test, etudiant@campuspulse.test')
    print('Le mot de passe est celui de DEMO_PASSWORD. Aucun email de démonstration envoyé.')


def _populate(db, password, created_files):
    secret = hash_password(password)
    def add(model, **values):
        obj = model(**values)
        db.add(obj)
        db.flush()
        return obj
    a = add(Campus, name='Université d’Antananarivo', code='UNA', slug='universite-antananarivo',
            description='Un campus ouvert sur le savoir, l’innovation et les initiatives étudiantes.',
            city='Antananarivo', country='Madagascar', address='Ankatso, Antananarivo 101', email='scolarite@example.com')
    b = add(Campus, name='Institut supérieur de Toamasina', code='IST', slug='institut-toamasina',
            description='Sciences, technologies et développement durable sur la côte Est.', city='Toamasina', country='Madagascar')
    add(CampusSettings, campus_id=a.id, allow_announcement_comments=True)
    add(CampusSettings, campus_id=b.id)
    platform = add(User, email='admin@campuspulse.test', password_hash=secret, first_name='Miora', last_name='Rabe', email_verified_at=utcnow())
    admin = add(User, email='responsable@campuspulse.test', password_hash=secret, first_name='Andry', last_name='Rakoto', email_verified_at=utcnow())
    student = add(User, email='etudiant@campuspulse.test', password_hash=secret, first_name='Sarah', last_name='Randria', phone='+261 34 00 000 00', email_verified_at=utcnow())
    classmate = add(User, email='lina@campuspulse.test', password_hash=secret, first_name='Lina', last_name='Rasolofoniaina', email_verified_at=utcnow())
    colleague = add(User, email='hery@campuspulse.test', password_hash=secret, first_name='Hery', last_name='Rajaonarivelo', email_verified_at=utcnow())
    admin_b = add(User, email='responsable.toamasina@campuspulse.test', password_hash=secret, first_name='Noro', last_name='Ravelo', email_verified_at=utcnow())
    outsider = add(User, email='etudiant.toamasina@campuspulse.test', password_hash=secret, first_name='Fano', last_name='Rakoto', email_verified_at=utcnow())
    add(RoleAssignment, user_id=platform.id, role='PLATFORM_ADMIN')
    for user, campus, role in [(admin,a,'CAMPUS_ADMIN'), (student,a,'STUDENT'), (classmate,a,'STUDENT'),
                               (colleague,a,'STUDENT'), (admin_b,b,'CAMPUS_ADMIN'), (outsider,b,'STUDENT')]:
        add(CampusMembership, user_id=user.id, campus_id=campus.id, membership_type='STAFF' if role == 'CAMPUS_ADMIN' else 'STUDENT')
        add(RoleAssignment, user_id=user.id, campus_id=campus.id, role=role, granted_by_user_id=platform.id)
        add(NotificationPreference, user_id=user.id)
    year = add(AcademicYear, campus_id=a.id, name='2026–2027', starts_on=date(2026,9,1), ends_on=date(2027,8,31), is_current=True)
    previous = add(AcademicYear, campus_id=a.id, name='2025–2026', starts_on=date(2025,9,1), ends_on=date(2026,8,31), status='ARCHIVED')
    year_b = add(AcademicYear, campus_id=b.id, name='2026–2027', starts_on=date(2026,9,1), ends_on=date(2027,8,31), is_current=True)
    computer = add(Program, campus_id=a.id, code='INFO', name='Informatique', description='Développement logiciel, données et systèmes numériques.')
    economics = add(Program, campus_id=a.id, code='ECO', name='Économie et gestion', description='Comprendre et piloter les organisations.')
    science_b = add(Program, campus_id=b.id, code='SCI', name='Sciences et environnement')
    l1 = add(ProgramLevel, program_id=computer.id, code='L1', name='Licence 1', level_order=1)
    l2 = add(ProgramLevel, program_id=computer.id, code='L2', name='Licence 2', level_order=2)
    l3 = add(ProgramLevel, program_id=computer.id, code='L3', name='Licence 3', level_order=3)
    eco_l1 = add(ProgramLevel, program_id=economics.id, code='L1', name='Licence 1', level_order=1)
    b_l1 = add(ProgramLevel, program_id=science_b.id, code='L1', name='Licence 1', level_order=1)
    algo = add(Subject, program_level_id=l2.id, code='ALGO2', name='Algorithmique avancée', credits=6, semester=3)
    database = add(Subject, program_level_id=l2.id, code='BDD', name='Bases de données relationnelles', credits=5, semester=3)
    web = add(Subject, program_level_id=l2.id, code='WEB', name='Développement web', credits=5, semester=3)
    add(Subject, program_level_id=l1.id, code='INTRO', name='Introduction à la programmation', credits=6, semester=1)
    add(Subject, program_level_id=eco_l1.id, code='MICRO', name='Microéconomie', credits=4, semester=1)
    for learner, level, academic_year, number, status in [(student,l1,previous,'UNA-2025-0042','COMPLETED'),
            (student,l2,year,'UNA-2026-0042','ACTIVE'), (classmate,l2,year,'UNA-2026-0057','ACTIVE'),
            (colleague,l2,year,'UNA-2026-0061','ACTIVE'), (outsider,b_l1,year_b,'IST-2026-0013','ACTIVE')]:
        add(Enrollment, user_id=learner.id, campus_id=b.id if learner is outsider else a.id, program_level_id=level.id,
            academic_year_id=academic_year.id, enrollment_number=number, status=status,
            completed_at=utcnow()-timedelta(days=45) if status == 'COMPLETED' else None, created_by_user_id=admin.id if learner is not outsider else admin_b.id)
    announcements = []
    for index, (title, summary, content, kind, pinned, targeted) in enumerate([
        ('Votre campus, toutes les informations au même endroit', 'Bienvenue sur CampusPulse, votre nouvel espace universitaire.',
         'Retrouvez ici les annonces officielles, vos ressources pédagogiques et les échanges de votre communauté.\n\nCommencez par consulter votre profil et votre parcours. Les documents de vos années précédentes restent accessibles dans la bibliothèque.\n\nBonne année universitaire à toutes et à tous !', 'GENERAL', True, False),
        ('Inscriptions pédagogiques : le calendrier est disponible', 'Les inscriptions du semestre sont ouvertes auprès de la scolarité.',
         'Les étudiants sont invités à vérifier leur inscription pédagogique et à déposer leur dossier complet auprès du service de scolarité.\n\nPièces à préparer : carte étudiante, fiche de renseignements et justificatif d’inscription.\n\nLa scolarité vous accueille du lundi au vendredi de 8 h à 16 h.', 'ADMINISTRATIVE', False, False),
        ('L2 Informatique : organisation des travaux pratiques', 'Retrouvez les groupes et consignes de préparation des TP.',
         'Les travaux pratiques d’algorithmique se déroulent en salle informatique B12. Préparez votre environnement Python et relisez le chapitre sur les structures de données.\n\nLe premier exercice sera réalisé en binôme. Consultez les supports disponibles dans la bibliothèque.', 'ACADEMIC', False, True),
        ('La bibliothèque universitaire élargit ses horaires', 'Un nouvel espace de travail pour préparer vos examens.',
         'La bibliothèque accueille désormais les étudiants jusqu’à 18 h du lundi au vendredi. Des salles de travail collectif peuvent être réservées à l’accueil.\n\nMerci de respecter le calme dans les espaces individuels.', 'GENERAL', False, False),
        ('Forum des associations étudiantes', 'Rencontrez les associations et choisissez votre prochain projet.',
         'Culture, sport, solidarité, entrepreneuriat : venez découvrir les associations du campus sur l’esplanade centrale.\n\nDes stands et des ateliers seront proposés toute la journée. L’entrée est libre pour tous les étudiants.', 'EVENT', False, False),
    ]):
        item = add(Announcement, campus_id=a.id, author_user_id=admin.id, title=title, summary=summary, content=content,
                   announcement_type=kind, scope='TARGETED' if targeted else 'CAMPUS', status='PUBLISHED',
                   is_pinned=pinned, allow_comments=True, published_at=utcnow()-timedelta(days=index), notifications_dispatched_at=utcnow(),
                   created_at=utcnow()-timedelta(days=index), level_ids=[l2.id] if targeted else [], year_ids=[year.id] if targeted else [])
        announcements.append(item)
    add(Announcement, campus_id=a.id, author_user_id=admin.id, title='Brouillon : réunion des délégués', content='Ordre du jour en cours de préparation.', status='DRAFT')
    add(Announcement, campus_id=b.id, author_user_id=admin_b.id, title='Sortie pédagogique sur le littoral', content='Cette annonce est réservée à l’Institut supérieur de Toamasina.', status='PUBLISHED', published_at=utcnow(), notifications_dispatched_at=utcnow())
    add(AnnouncementComment, announcement_id=announcements[0].id, author_user_id=student.id, content='Merci ! Les ressources des années précédentes sont vraiment utiles pour réviser.')
    now = utcnow().replace(minute=0, second=0, microsecond=0)
    for title, description, location, offset, duration in [
        ('Forum des associations', 'Découvrez les associations étudiantes et rencontrez leurs équipes.', 'Esplanade centrale', 3, 6),
        ('Atelier : réussir son CV', 'Un atelier pratique avec le service insertion professionnelle. Pensez à apporter votre ordinateur.', 'Amphithéâtre A', 5, 2),
        ('Conférence : les métiers du numérique', 'Échanges avec des diplômés et professionnels du développement logiciel.', 'Salle de conférence B', 8, 3),
        ('Tournoi sportif inter-filières', 'Une journée conviviale organisée par l’association sportive du campus.', 'Terrain universitaire', 12, 5),
    ]:
        start = now + timedelta(days=offset)
        add(Event, campus_id=a.id, created_by_user_id=admin.id, title=title, description=description,
            location=location, starts_at=start, ends_at=start+timedelta(hours=duration), status='PUBLISHED')
    for title, category, subject, body in [
        ('Algorithmique — Structures de données', 'COURSE', algo, 'Objectifs : comprendre les piles, files et arbres.\n\nUne pile suit le principe dernier entré, premier sorti. Une file traite les éléments dans leur ordre d’arrivée.\n\nExercice : implémenter une pile et vérifier ses opérations avec des exemples.'),
        ('Bases de données — Exercices SQL', 'EXERCISE', database, '1. Créer une table étudiants avec une clé primaire.\n2. Écrire une requête SELECT filtrant les inscriptions actives.\n3. Joindre étudiants et inscriptions.\n4. Grouper les inscriptions par année universitaire.'),
        ('Développement web — Fiche de révision', 'SUMMARY', web, 'HTTP : méthodes GET, POST, PATCH et DELETE.\nValidation : contrôler les données sur le serveur.\nAuthentification : identifier un utilisateur.\nAutorisation : vérifier ses permissions sur chaque ressource.\nAccessibilité : labels, focus visible et navigation clavier.'),
        ('Algorithmique — Corrigé du TD 1', 'SOLUTION', algo, 'Pour une recherche séquentielle, la complexité est O(n).\nPour une recherche dichotomique sur une liste triée, elle est O(log n).\nToujours préciser les hypothèses et tester les cas limites : liste vide, un seul élément et élément absent.'),
        ('Bases de données — Sujet d’entraînement', 'EXAM', database, 'Durée conseillée : 90 minutes.\n\nPartie 1 : dessiner le modèle relationnel d’une bibliothèque.\nPartie 2 : proposer les contraintes d’intégrité.\nPartie 3 : rédiger trois requêtes utiles pour le bibliothécaire.'),
    ]:
        data = f'CampusPulse — Ressource pédagogique de démonstration\n{title}\n\n{body}\n\nCe support fictif sert à démontrer les fonctionnalités de la plateforme.\n'.encode('utf-8')
        key = f'{uuid4().hex}.txt'
        path = file_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        created_files.append(path)
        asset = add(FileAsset, campus_id=a.id, uploaded_by_user_id=admin.id, storage_key=key,
                    original_filename=f'{subject.code.lower()}-{category.lower()}.txt', mime_type='text/plain', extension='.txt',
                    size_bytes=len(data), sha256_hash=hashlib.sha256(data).hexdigest())
        add(Document, campus_id=a.id, file_asset_id=asset.id, uploaded_by_user_id=admin.id, subject_id=subject.id,
            title=title, description='Support pédagogique pour les étudiants de Licence 2 Informatique.', category=category,
            scope='TARGETED', level_ids=[l2.id], year_ids=[year.id], status='PUBLISHED', published_at=utcnow())
    posts = []
    for author, title, content, kind in [
        (classmate, 'Un groupe pour réviser les bases de données ?', 'Je propose une séance de révision jeudi après les cours à la bibliothèque. On pourrait reprendre les jointures SQL ensemble. Qui est partant ?', 'QUESTION'),
        (colleague, 'Retour sur l’atelier développement web', 'L’atelier de cette semaine était très intéressant ! J’ai surtout retenu l’importance de vérifier les permissions côté serveur. Merci aux organisateurs.', 'DISCUSSION'),
        (student, 'Mes conseils pour bien commencer le semestre', 'Préparez votre planning, consultez régulièrement les annonces et n’hésitez pas à poser des questions. Un petit groupe de travail fait toute la différence !', 'RESOURCE'),
        (classmate, 'À la recherche de partenaires pour un projet', 'Nous cherchons deux personnes motivées pour construire un petit outil de réservation de salles. Débutants bienvenus, l’objectif est d’apprendre ensemble.', 'DISCUSSION'),
    ]:
        posts.append(add(CommunityPost, campus_id=a.id, author_user_id=author.id, title=title, content=content, post_type=kind))
    add(CommunityComment, post_id=posts[0].id, author_user_id=student.id, content='Partante ! Je prépare quelques exercices sur les jointures et les agrégations.')
    add(CommunityComment, post_id=posts[0].id, author_user_id=colleague.id, content='Je vous rejoins vers 14 h. On se retrouve au deuxième étage ?')
    add(Reaction, user_id=student.id, post_id=posts[0].id)
    add(Reaction, user_id=colleague.id, post_id=posts[0].id)
    add(Reaction, user_id=classmate.id, post_id=posts[2].id)
    for recipient in (student, classmate, colleague, admin):
        for item in announcements[:3]:
            add(Notification, user_id=recipient.id, campus_id=a.id, event_key=f'announcements:{item.id}:published',
                notification_type='ANNOUNCEMENT', title=item.title, message=item.summary or 'Une nouvelle annonce vous concerne.', link=f'/app/announcements/{item.id}')
    add(PlatformSetting, key='general', value={'platform_name':'CampusPulse','support_email':'support@example.com','maintenance_message':None})
    add(AuditLog, actor_user_id=platform.id, action='demo.initialize', entity_type='campuses', entity_id=a.id,
        details={'description':'Initialisation explicite de la démonstration locale.'})


if __name__ == '__main__':
    seed()
