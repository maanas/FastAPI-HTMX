import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import delete

ROOT = Path(__file__).resolve().parents[2]

# The suite runs on its own throwaway SQLite file, never on the DATABASE_URL of the
# shell or .env. app.database.base reads DATABASE_URL and builds the engine at import
# time, so the variable is overwritten here, before the app is imported (a test
# subprocess inherits it). The schema comes from the migrations, so the suite also
# proves that `alembic upgrade head` works.
REAL_DATABASE_URL = os.environ.get("DATABASE_URL")
TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="pytest-db-"))
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_DIR / 'test.db'}"
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
    shutil.rmtree(TEST_DB_DIR, ignore_errors=True)
    raise pytest.UsageError(
        f"alembic upgrade head failed on the test database:\n{error.stderr[-1000:]}"
    ) from None

from app.database.base import async_session_maker, engine, init_models  # noqa: E402

if str(engine.url) != TEST_DATABASE_URL:
    raise pytest.UsageError("the tests must run on their own throwaway database")


def pytest_unconfigure(config):
    shutil.rmtree(TEST_DB_DIR, ignore_errors=True)


TEST_ROLE_PREFIX = "pytest-"


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
