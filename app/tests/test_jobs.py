import importlib
import importlib.metadata
import importlib.util
import os
import subprocess
import sys

import pytest
from loguru import logger
from procrastinate.schema import SchemaManager
from procrastinate.testing import InMemoryConnector
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from app import jobs
from app.database.base import engine
from app.tests.conftest import ROOT, TEST_DATABASE_URL


@pytest.fixture
def memory_app():
    with jobs.app.replace_connector(InMemoryConnector()) as app:
        yield app


@pytest.mark.anyio
async def test_defer_queues_one_job(memory_app, anyio_backend):
    await jobs.log_message.defer_async(message="hello")

    queued = list(memory_app.connector.jobs.values())
    assert len(queued) == 1
    assert queued[0]["task_name"] == "log_message"
    assert queued[0]["queue_name"] == "default"
    assert queued[0]["args"] == {"message": "hello"}


@pytest.mark.anyio
async def test_worker_runs_the_job_and_logs_the_line(memory_app, anyio_backend):
    lines = []
    sink = logger.add(lambda m: lines.append(m.record["message"]), level="INFO")
    try:
        await jobs.log_message.defer_async(message="hello")
        await memory_app.run_worker_async(wait=False)
    finally:
        logger.remove(sink)

    assert "job message: hello" in lines
    assert [j["status"] for j in memory_app.connector.jobs.values()] == ["succeeded"]


@pytest.mark.anyio
async def test_migration_created_the_procrastinate_tables(anyio_backend):
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE tablename ~ '^procrastinate'")
        )
    assert {r[0] for r in rows} >= {"procrastinate_jobs", "procrastinate_events"}


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql+asyncpg://u:p@h:5434/d", "postgresql://u:p@h:5434/d"),
        ("postgresql+asyncpg://u:p@h/d?ssl=require", "postgresql://u:p@h/d?sslmode=require"),
        ("postgresql+asyncpg://u:p@h/d?ssl=verify-full", "postgresql://u:p@h/d?sslmode=verify-full"),
        ("postgresql+asyncpg://u:p@h/d?sslmode=disable", "postgresql://u:p@h/d?sslmode=disable"),
    ],
)
def test_psycopg_conninfo_maps_the_ssl_parameter(url, expected):
    assert jobs.psycopg_conninfo(url) == expected


def test_psycopg_conninfo_keeps_sslmode_when_both_are_given():
    result = make_url(jobs.psycopg_conninfo("postgresql+asyncpg://u:p@h/d?ssl=require&sslmode=allow"))
    assert dict(result.query) == {"sslmode": "allow"}


def test_psycopg_conninfo_keeps_a_password_with_special_characters():
    password = "p@ss:w/rd%20#?&="
    url = URL.create(
        "postgresql+asyncpg", "u", password, "h", 5434, "d", {"ssl": "require"}
    ).render_as_string(hide_password=False)

    parsed = make_url(jobs.psycopg_conninfo(url))

    assert parsed.password == password
    assert parsed.drivername == "postgresql"
    assert dict(parsed.query) == {"sslmode": "require"}


def test_offline_upgrade_renders_the_procrastinate_schema():
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    )
    expected = SchemaManager.get_schema().strip().rstrip(";") + ";"
    assert "CREATE TABLE procrastinate_jobs" in result.stdout
    assert expected in result.stdout  # `::` casts and `:word` come out unchanged


def test_procrastinate_version_matches_the_0002_schema():
    path = ROOT / "app/migrations/versions/0002_procrastinate.py"
    spec = importlib.util.spec_from_file_location("migration_0002", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert importlib.metadata.version("procrastinate") == migration.PROCRASTINATE_VERSION, (
        "procrastinate changed: add a migration that runs procrastinate's SQL migrations "
        "(procrastinate/sql/migrations) for the versions in between, then update "
        "PROCRASTINATE_VERSION (see the docstring of 0002_procrastinate.py)"
    )
