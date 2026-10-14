import uuid

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models.groups import Group, Permission


def _name() -> str:
    return f"pytest-{uuid.uuid4().hex[:12]}"


async def _cleanup(db_session, *names: str) -> None:
    await db_session.rollback()
    for name in names:
        await db_session.execute(
            text('DELETE FROM "group" WHERE group_name = :n'), {"n": name}
        )
    await db_session.commit()


@pytest.mark.anyio
async def test_group_saves_and_reloads_permission(db_session):
    name = _name()
    group = Group(group_name=name, permission=Permission.WRITE)
    db_session.add(group)
    await db_session.commit()
    group_id = group.id
    try:
        raw = (
            await db_session.execute(
                text('SELECT permission FROM "group" WHERE group_name = :n'),
                {"n": name},
            )
        ).scalar_one()
        assert raw == "write"
        db_session.expire_all()
        reloaded = await db_session.get(Group, group_id)
        assert reloaded.permission is Permission.WRITE
    finally:
        await _cleanup(db_session, name)


@pytest.mark.anyio
async def test_database_refuses_unknown_permission(db_session):
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                'INSERT INTO "group" (id, group_name, permission) '
                "VALUES (:id, :n, 'superuser')"
            ),
            {"id": uuid.uuid4().hex, "n": _name()},
        )
    await db_session.rollback()


@pytest.mark.anyio
async def test_permission_may_be_null(db_session):
    name = _name()
    db_session.add(Group(group_name=name))
    await db_session.commit()
    try:
        raw = (
            await db_session.execute(
                text('SELECT permission FROM "group" WHERE group_name = :n'),
                {"n": name},
            )
        ).scalar_one()
        assert raw is None
    finally:
        await _cleanup(db_session, name)


@pytest.mark.anyio
async def test_group_table_has_permission_check_constraint(db_session):
    conn = await db_session.connection()
    checks = await conn.run_sync(
        lambda c: inspect(c).get_check_constraints("group")
    )
    assert "ck_group_permission" in {c["name"] for c in checks}
