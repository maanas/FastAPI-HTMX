import pytest
from loguru import logger
from procrastinate.testing import InMemoryConnector
from sqlalchemy import text

from app import jobs
from app.database.base import engine


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
