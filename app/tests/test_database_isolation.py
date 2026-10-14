"""The suite runs on its own database and never touches the configured one."""

import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect

from app.database.base import engine
from app.tests.conftest import REAL_DATABASE_URL, ROOT, TEST_DATABASE_URL, TEST_DB_DIR


def test_engine_uses_the_throwaway_database():
    assert str(engine.url) == TEST_DATABASE_URL
    assert os.environ["DATABASE_URL"] == TEST_DATABASE_URL
    assert TEST_DATABASE_URL != REAL_DATABASE_URL
    assert str(TEST_DB_DIR) in TEST_DATABASE_URL


@pytest.mark.anyio
async def test_schema_comes_from_the_migrations(db_session):
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert "alembic_version" in tables


def test_subprocess_inherits_the_test_database():
    result = subprocess.run(
        [sys.executable, "-c", "import app.database.base as b; print(b.engine.url)"],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == TEST_DATABASE_URL, result.stderr[-500:]
