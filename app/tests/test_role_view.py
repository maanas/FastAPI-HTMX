import html
import json
import re
import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.app import app
from app.database.security import current_active_user
from app.models.users import Role

from .conftest import TEST_ROLE_PREFIX

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
ROLE_NAME = TEST_ROLE_PREFIX + "view-role"


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


@pytest.fixture
async def stored_role(db_session):
    # conftest removes every role named with the pytest- prefix afterwards
    role = Role(role_name=ROLE_NAME, role_desc="A role for the view tests")
    db_session.add(role)
    await db_session.commit()
    return role


def assert_full_page(response):
    assert response.status_code == 200
    assert response.text.count("<nav") == 1
    assert response.text.count("<aside") == 1
    assert 'id="dashboard-body"' in response.text
    assert "HX-Request" in response.headers["vary"]


def assert_fragment(response):
    assert response.status_code == 200
    assert "<nav" not in response.text
    assert "<aside" not in response.text
    assert "<html" not in response.text
    assert response.text.lstrip().startswith('<div id="dashboard-body"')
    assert response.text.count('id="dashboard-body"') == 1
    assert "HX-Request" in response.headers["vary"]


async def test_role_list_full_request_is_a_page(client, logged_in, stored_role):
    response = await client.get("/role")
    assert_full_page(response)
    assert ROLE_NAME in response.text
    assert ">Groups<" in response.text  # user_type keeps the admin links


async def test_role_list_htmx_request_is_a_fragment(client, logged_in, stored_role):
    response = await client.get("/role", headers=HX)
    assert_fragment(response)
    assert ROLE_NAME in response.text
    assert 'id="role-page"' in response.text
    assert "X-Role-Name" not in response.text


async def test_history_restore_request_gets_the_full_page(client, logged_in):
    response = await client.get(
        "/role", headers={**HX, "HX-History-Restore-Request": "true"}
    )
    assert_full_page(response)


async def test_add_form_page_and_fragment(client, logged_in):
    page = await client.get("/get_create_roles")
    assert_full_page(page)
    assert 'id="create-role-form"' in page.text
    fragment = await client.get("/get_create_roles", headers=HX)
    assert_fragment(fragment)
    assert 'id="create-role-form"' in fragment.text


async def test_edit_form_page_and_fragment(client, logged_in, stored_role):
    url = f"/get_role/{stored_role.id}"
    page = await client.get(url)
    assert_full_page(page)
    assert 'id="edit-role-form"' in page.text
    fragment = await client.get(url, headers=HX)
    assert_fragment(fragment)
    assert 'id="edit-role-form"' in fragment.text
    assert f'value="{ROLE_NAME}"' in fragment.text


async def test_error_response_follows_the_request_kind(client, logged_in):
    logged_in.is_superuser = False
    unknown = "/get_role/00000000-0000-0000-0000-000000000000"
    for url in ("/role", "/get_create_roles", unknown):
        fragment = await client.get(url, headers=HX)
        assert_fragment(fragment)
        assert "Not authorized" in fragment.text
        page = await client.get(url)
        assert page.text.count("<nav") == 1
        assert "Not authorized" in page.text


async def csrf_token_from(client):
    page = await client.get("/role", headers=HX)
    return re.search(r'"X-CSRF-Token":\s*"([^"]+)"', page.text).group(1)


async def role_exists(db_session):
    db_session.expire_all()
    found = await db_session.execute(select(Role).where(Role.role_name == ROLE_NAME))
    return found.scalar_one_or_none() is not None


async def test_delete_needs_the_csrf_token(client, logged_in, stored_role, db_session):
    response = await client.delete(f"/delete_role/{stored_role.id}", headers=HX)
    assert "HX-Location" not in response.headers
    assert "<nav" not in response.text
    assert "Missing Cookie: `fastapi-csrf-token`" in response.text
    assert await role_exists(db_session)


async def test_delete_names_the_database_role_not_the_header(
    client, logged_in, stored_role, db_session
):
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete_role/{stored_role.id}",
        headers={**HX, "X-CSRF-Token": token, "X-Role-Name": "Spoofed name"},
    )
    assert response.status_code == 200
    assert json.loads(response.headers["HX-Location"]) == {
        "path": "/role",
        "target": "#dashboard-body",
        "swap": "outerHTML",
    }
    message = json.loads(response.headers["HX-Trigger"])["showAlert"]["message"]
    assert message == f"{ROLE_NAME} deleted successfully"
    assert "Spoofed" not in response.headers["HX-Trigger"]
    assert not await role_exists(db_session)


async def test_delete_is_refused_for_a_regular_user(
    client, logged_in, stored_role, db_session
):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.delete(
        f"/delete_role/{stored_role.id}",
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" not in response.headers
    assert "Not authorized" in response.text
    assert await role_exists(db_session)


async def test_quotes_in_a_role_name_stay_escaped_in_attributes(
    client, logged_in, db_session
):
    name = TEST_ROLE_PREFIX + "q\"uote's"
    db_session.add(Role(role_name=name, role_desc="quotes"))
    await db_session.commit()
    role = (
        await db_session.execute(select(Role).where(Role.role_name == name))
    ).scalar_one()

    listing = await client.get("/role", headers=HX)
    assert name not in listing.text
    assert "pytest-q&#34;uote&#39;s" in listing.text
    attr = re.search(r"id=\"role-page\".*?hx-headers='([^']*)'", listing.text, re.S)
    assert "X-CSRF-Token" in json.loads(html.unescape(attr.group(1)))

    edit = await client.get(f"/get_role/{role.id}", headers=HX)
    value = re.search(r'name="role_name".*?value="([^"]*)"', edit.text, re.S)
    assert '"' not in value.group(1)
    assert html.unescape(value.group(1)) == name


async def test_rename_to_an_existing_name_is_an_error_not_a_500(
    client, logged_in, stored_role, db_session
):
    other = Role(role_name=ROLE_NAME + "-other", role_desc="Another role")
    db_session.add(other)
    await db_session.commit()
    other_id = other.id
    token = await csrf_token_from(client)
    response = await client.put(
        f"/post_update_role/{other_id}",
        data={"role_name": ROLE_NAME, "role_desc": "Another role"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 200
    assert "HX-Location" not in response.headers
    assert "already exists" in response.text
    assert 'id="edit-role-form"' in response.text
    db_session.expire_all()
    names = (
        await db_session.execute(
            select(Role.role_name).where(Role.role_name.like(ROLE_NAME + "%"))
        )
    ).scalars()
    assert sorted(names) == [ROLE_NAME, ROLE_NAME + "-other"]
