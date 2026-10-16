import asyncio
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]

# The suite runs on its own throwaway Postgres database, never on the DATABASE_URL of
# the shell or .env. The server is TEST_DATABASE_URL (default: the compose server, start
# it with `docker compose up -d --wait db`); a database pytest_<hex> is created on it
# and dropped at the end. app.database.base reads DATABASE_URL and builds the engine at
# import time, so the variable is overwritten here, before the app is imported (a test
# subprocess inherits it). The schema comes from the migrations, so the suite also
# proves that `alembic upgrade head` works.
REAL_DATABASE_URL = os.environ.get("DATABASE_URL")
DEFAULT_SERVER_URL = (
    "postgresql+asyncpg://fastapi_htmx:fastapi_htmx@127.0.0.1:5434/fastapi_htmx"
)
SERVER_URL = make_url(os.environ.get("TEST_DATABASE_URL", DEFAULT_SERVER_URL))
TEST_DB_NAME = f"pytest_{secrets.token_hex(6)}"
TEST_DATABASE_URL = SERVER_URL.set(database=TEST_DB_NAME).render_as_string(
    hide_password=False
)


async def _admin(statement: str) -> None:
    """Run one statement on the maintenance database, outside a transaction."""
    admin = create_async_engine(
        SERVER_URL.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        async with admin.connect() as conn:
            await conn.execute(text(statement))
    finally:
        await admin.dispose()


try:
    asyncio.run(_admin(f'CREATE DATABASE "{TEST_DB_NAME}"'))
except Exception as error:
    raise pytest.UsageError(
        f"cannot reach the test Postgres server ({type(error).__name__}); "
        "run `docker compose up -d --wait db` or set TEST_DATABASE_URL"
    ) from None

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Test-only signing key, set before the app is imported (env beats .env).
os.environ.setdefault(
    "AUTH_SECRET", "pytest-only-auth-secret-not-for-use-0123456789abcdef"
)

try:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        capture_output=True,
        text=True,
    )
except subprocess.CalledProcessError as error:
    asyncio.run(_admin(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
    raise pytest.UsageError(
        f"alembic upgrade head failed on the test database:\n{error.stderr[-1000:]}"
    ) from None

from app.database.base import async_session_maker, engine, init_models  # noqa: E402

if engine.url.render_as_string(hide_password=False) != TEST_DATABASE_URL:
    asyncio.run(_admin(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
    raise pytest.UsageError("the tests must run on their own throwaway database")


def pytest_unconfigure(config):
    asyncio.run(_admin(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))


TEST_ROLE_PREFIX = "pytest-"


@pytest.fixture(autouse=True)
def fresh_pool():
    """Each test runs in its own event loop, and an asyncpg connection is bound to the
    loop that opened it: start every test with an empty pool."""
    engine.sync_engine.dispose(close=False)
    yield
    engine.sync_engine.dispose(close=False)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session(anyio_backend):
    """A session on the throwaway test database; test roles are deleted afterwards."""
    from app.models.users import Role

    init_models()
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.execute(
                delete(Role).where(Role.role_name.like(f"{TEST_ROLE_PREFIX}%"))
            )
            await session.commit()
    # Each test runs in its own event loop, so drop pooled connections.
    await engine.dispose()
