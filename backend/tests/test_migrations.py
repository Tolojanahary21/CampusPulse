import os
from pathlib import Path
import subprocess
import sys


def test_migration_upgrade_schema_check_and_roundtrip(tmp_path):
    database = tmp_path / 'migration.sqlite3'
    env = {**os.environ, 'DATABASE_URL': f'sqlite+pysqlite:///{database.as_posix()}', 'APP_ENV': 'test', 'SMTP_ENABLED': 'false', 'APP_DEBUG': 'false'}
    backend = Path(__file__).resolve().parents[1]
    for command in (['upgrade', 'head'], ['check'], ['downgrade', 'base'], ['upgrade', 'head']):
        result = subprocess.run([sys.executable, '-m', 'alembic', *command], cwd=backend, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
