import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.users import Role
from app.routes.view.view_crud import SQLAlchemyCRUD

from .conftest import TEST_ROLE_PREFIX

pytestmark = pytest.mark.anyio

NAME = f"{TEST_ROLE_PREFIX}editor"


async def test_role_is_stored_and_read_back_by_name(db_session):
    db_session.add(Role(role_name=NAME, role_desc="Can edit"))
    await db_session.commit()

    result = await db_session.execute(select(Role).filter_by(role_name=NAME))
    role = result.scalars().one()
    assert role.role_desc == "Can edit"
    assert role.id is not None


async def test_duplicate_role_name_raises_integrity_error(db_session):
    db_session.add(Role(role_name=NAME, role_desc="first"))
    await db_session.commit()

    db_session.add(Role(role_name=NAME, role_desc="second"))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_crud_create_then_read_by_column(db_session):
    crud = SQLAlchemyCRUD(Role)

    data = {"role_name": NAME, "role_desc": "Can edit"}
    created = await crud.create(data, db_session)
    found = await crud.read_by_column(db_session, "role_name", NAME.upper())

    assert found.id == created.id


async def test_crud_read_by_column_returns_none_when_missing(db_session):
    crud = SQLAlchemyCRUD(Role)

    assert await crud.read_by_column(db_session, "role_name", f"{NAME}-missing") is None
