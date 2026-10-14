from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

engine_options = {'pool_pre_ping': True}
if settings.database_url.startswith('sqlite'):
    engine_options['connect_args'] = {'check_same_thread': False}
    if ':memory:' in settings.database_url:
        engine_options['poolclass'] = StaticPool

engine = create_engine(settings.database_url, **engine_options)
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_constraints(connection, _):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise
