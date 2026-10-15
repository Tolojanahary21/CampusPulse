from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

engine_options = {'pool_pre_ping': True}
if settings.database_url.startswith('sqlite'):
    engine_options['connect_args'] = {'check_same_thread': False}
    if ':memory:' in settings.database_url:
        engine_options['poolclass'] = StaticPool
else:
    # Bound connections per API/worker process so replica count cannot silently
    # multiply SQLAlchemy's default overflow against a small database server.
    engine_options.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=1800,
    )

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
