"""permission enum

Revision ID: 0002_permission_enum
Revises: 0001_initial_schema
Create Date: 2026-10-14 17:21:31.046340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import fastapi_users_db_sqlalchemy  # noqa: F401  (GUID column type)


# revision identifiers, used by Alembic.
revision: str = '0002_permission_enum'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Old rows may hold any string (the column was unconstrained). Set a value
    # outside the four to NULL so the CHECK constraint cannot fail the upgrade.
    op.execute(
        "UPDATE \"group\" SET permission = NULL "
        "WHERE permission NOT IN ('read', 'write', 'delete', 'admin')"
    )
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.alter_column('permission',
               existing_type=sa.String(),
               type_=sa.String(length=16),
               existing_nullable=True)
        batch_op.create_check_constraint(
            op.f('ck_group_permission'),
            "permission IN ('read', 'write', 'delete', 'admin')",
        )


def downgrade() -> None:
    with op.batch_alter_table('group', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_group_permission'), type_='check')
        batch_op.alter_column('permission',
               existing_type=sa.String(length=16),
               type_=sa.String(),
               existing_nullable=True)
