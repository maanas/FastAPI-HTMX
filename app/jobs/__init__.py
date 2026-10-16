import procrastinate
from loguru import logger
from sqlalchemy.engine import make_url

from app.database.base import DATABASE_URL


def psycopg_conninfo(url: str) -> str:
    """Turn the SQLAlchemy asyncpg URL into a libpq URL for psycopg.

    asyncpg's `ssl` query parameter becomes libpq's `sslmode` (same value names). The result
    holds the password: never log it.
    """
    parsed = make_url(url).set(drivername="postgresql")
    query = dict(parsed.query)
    if "ssl" in query:
        mode = query.pop("ssl")
        query.setdefault("sslmode", mode)
    return parsed.set(query=query).render_as_string(hide_password=False)


# Worker, also runs periodic tasks:
#   .venv/bin/python -m procrastinate --app=app.jobs.app worker
app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        conninfo=psycopg_conninfo(DATABASE_URL)
    ),
)


@app.task(queue="default", name="log_message")
async def log_message(message: str) -> None:
    logger.info("job message: {}", message)
