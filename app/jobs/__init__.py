import procrastinate
from loguru import logger

from app.database.base import DATABASE_URL

# Worker, also runs periodic tasks:
#   .venv/bin/python -m procrastinate --app=app.jobs.app worker
app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        conninfo=DATABASE_URL.replace("+asyncpg", "")
    ),
)


@app.task(queue="default", name="log_message")
async def log_message(message: str) -> None:
    logger.info("job message: {}", message)
