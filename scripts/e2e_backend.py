"""Isolated backend for Playwright. Uses only .qa/e2e.sqlite3, never a user's DB."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    qa = root / '.qa'
    qa.mkdir(exist_ok=True)
    database = (qa / 'e2e.sqlite3').resolve()
    if database.parent != qa.resolve() or not database.is_relative_to(root):
        raise SystemExit('Unexpected E2E database path.')
    # This explicitly named, disposable database belongs only to this test server.
    database.unlink(missing_ok=True)
    env = os.environ.copy()
    env.update(APP_ENV='test', APP_DEBUG='false', DATABASE_URL=f'sqlite+pysqlite:///{database.as_posix()}', STORAGE_PATH=str(qa / 'e2e-storage'), SMTP_ENABLED='false', COOKIE_SECURE='false', COOKIE_DOMAIN='', SECRET_KEY='isolated-e2e-test-secret-never-for-production', FRONTEND_URL='http://localhost:3101', CORS_ORIGINS='["http://localhost:3101"]', TRUSTED_HOSTS='["localhost","127.0.0.1"]', DEMO_PASSWORD='CampusPulse-e2e-2026!')
    env['PUBLIC_REGISTRATION_ENABLED'] = 'true'
    backend = root / 'backend'
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=backend, env=env, check=True)
    subprocess.run([sys.executable, '-m', 'app.seed'], cwd=backend, env=env, check=True)
    os.chdir(backend)
    os.environ.update(env)
    sys.path.insert(0, str(backend))
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=8001)


if __name__ == '__main__':
    main()
