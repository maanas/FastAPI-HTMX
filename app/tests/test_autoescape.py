import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.app import app
from app.database.security import current_active_user
from app.models.groups import Group
from app.models.users import Role
from app.templates import jinja_env

from .conftest import TEST_ROLE_PREFIX

pytestmark = pytest.mark.anyio

PAYLOAD = "<script>alert(1)</script>"
ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;"
GROUP_NAME = "pytest-" + PAYLOAD


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def logged_in():
    user = SimpleNamespace(
        id=uuid.uuid4(), email="admin@example.com", is_superuser=True
    )
    app.dependency_overrides[current_active_user] = lambda: user
    yield user
    app.dependency_overrides.pop(current_active_user, None)


def test_environment_escapes_html_templates():
    page = jinja_env.get_template("pages/index.html")
    assert page.environment.autoescape(page.name) is True


async def test_role_name_is_escaped_on_the_role_page(client, logged_in, db_session):
    db_session.add(Role(role_name=TEST_ROLE_PREFIX + PAYLOAD, role_desc=PAYLOAD))
    await db_session.commit()
    response = await client.get("/role")
    assert response.status_code == 200
    assert PAYLOAD not in response.text
    assert ESCAPED in response.text
    # the JSON header attribute stays valid: quotes and angle brackets are \u-escaped
    assert "\\u003cscript\\u003e" in response.text


async def test_group_name_is_escaped_on_the_groups_page(client, logged_in, db_session):
    db_session.add(Group(group_name=GROUP_NAME, group_desc=PAYLOAD))
    await db_session.commit()
    try:
        response = await client.get("/groups")
        assert response.status_code == 200
        assert PAYLOAD not in response.text
        assert ESCAPED in response.text
        assert "\\u003cscript\\u003e" in response.text
    finally:
        await db_session.rollback()
        await db_session.execute(delete(Group).where(Group.group_name == GROUP_NAME))
        await db_session.commit()
