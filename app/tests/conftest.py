import pytest
from sqlalchemy import delete

from app.database.base import Base, async_session_maker, engine, init_models

TEST_ROLE_PREFIX = "pytest-"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session(anyio_backend):
    """A session on the configured database; test roles are deleted afterwards."""
    from app.models.users import Role

    init_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
