"""procrastinate job queue schema

Revision ID: 0002_procrastinate
Revises: 0001_initial_schema
Create Date: 2026-10-16 12:00:00

The schema is procrastinate's own SQL for the installed version. A procrastinate upgrade needs a
new revision that runs the files from procrastinate/sql/migrations for the versions in between.
"""

from collections.abc import Sequence

from alembic import op
from procrastinate.schema import SchemaManager
from sqlalchemy.util import await_only

revision: str = "0002_procrastinate"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def run_script(sql: str) -> None:
    # asyncpg prepares statements, which allow one command; its execute() without arguments
    # uses the simple query protocol and runs a whole multi-statement script.
    driver = op.get_bind().connection.driver_connection
    assert driver is not None, "migration needs an open asyncpg connection"
    await_only(driver.execute(sql))


def upgrade() -> None:
    run_script(SchemaManager.get_schema())


def downgrade() -> None:
    run_script(
        """
        DROP TABLE IF EXISTS procrastinate_events, procrastinate_periodic_defers,
            procrastinate_jobs, procrastinate_workers CASCADE;
        DO $$
        DECLARE f regprocedure;
        BEGIN
            FOR f IN SELECT oid::regprocedure FROM pg_proc WHERE proname LIKE 'procrastinate%'
            LOOP
                EXECUTE 'DROP FUNCTION ' || f || ' CASCADE';
            END LOOP;
        END $$;
        DROP TYPE IF EXISTS procrastinate_job_status, procrastinate_job_event_type,
            procrastinate_job_to_defer_v1 CASCADE;
        """
    )
