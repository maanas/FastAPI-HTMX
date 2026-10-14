import json
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from app.app import app
from app.database.security import current_active_user
from app.models.users import Role, User, UserProfile

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
EMAIL = "pytest-user-view@example.com"


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
async def stored_user(db_session):
    profile = UserProfile(first_name="Ada", last_name="Lovelace")
    db_session.add(profile)
    await db_session.flush()
    user = User(
        email=EMAIL,
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        is_verified=False,
        profile_id=profile.id,
    )
    db_session.add(user)
    await db_session.commit()
    user_id, profile_id = user.id, profile.id
    yield user
    await db_session.rollback()
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.execute(delete(UserProfile).where(UserProfile.id == profile_id))
    await db_session.commit()


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


async def test_user_list_full_request_is_a_page(client, logged_in, stored_user):
    response = await client.get("/user")
    assert_full_page(response)
    assert EMAIL in response.text


async def test_user_list_htmx_request_is_a_fragment(client, logged_in, stored_user):
    response = await client.get("/user", headers=HX)
    assert_fragment(response)
    assert EMAIL in response.text
    assert 'id="user-page"' in response.text


async def test_history_restore_request_gets_the_full_page(client, logged_in):
    response = await client.get(
        "/user", headers={**HX, "HX-History-Restore-Request": "true"}
    )
    assert_full_page(response)


async def test_add_form_page_and_fragment(client, logged_in):
    assert_full_page(await client.get("/get_create_users"))
    assert_fragment(await client.get("/get_create_users", headers=HX))


async def test_edit_form_page_and_fragment(client, logged_in, stored_user):
    url = f"/get_user/{stored_user.id}"
    page = await client.get(url)
    assert_full_page(page)
    assert 'id="edit-user-form"' in page.text
    fragment = await client.get(url, headers=HX)
    assert_fragment(fragment)
    assert 'id="edit-user-form"' in fragment.text
    assert 'value="Ada"' in fragment.text


async def test_error_response_follows_the_request_kind(client, logged_in):
    logged_in.is_superuser = False
    fragment = await client.get("/user", headers=HX)
    assert_fragment(fragment)
    assert "Not authorized" in fragment.text
    page = await client.get("/user")
    assert page.text.count("<nav") == 1
    assert "Not authorized" in page.text
    edit = await client.get(
        "/get_user/00000000-0000-0000-0000-000000000000", headers=HX
    )
    assert_fragment(edit)
    assert "Not authorized" in edit.text


async def csrf_token_from(client):
    page = await client.get("/user", headers=HX)
    return re.search(r'"X-CSRF-Token": "([^"]+)"', page.text).group(1)


async def test_delete_needs_the_csrf_token(client, logged_in, stored_user, db_session):
    response = await client.delete(f"/delete_user/{stored_user.id}", headers=HX)
    assert "HX-Location" not in response.headers
    assert "<nav" not in response.text
    assert "Missing Cookie: `fastapi-csrf-token`" in response.text
    db_session.expire_all()
    found = await db_session.execute(select(User).where(User.email == EMAIL))
    assert found.scalar_one_or_none() is not None


async def test_delete_with_the_token_removes_the_user(
    client, logged_in, stored_user, db_session
):
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete_user/{stored_user.id}",
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 200
    assert '"path": "/user"' in response.headers["HX-Location"]
    assert "deleted successfully" in response.headers["HX-Trigger"]
    db_session.expire_all()
    found = await db_session.execute(select(User).where(User.email == EMAIL))
    assert found.scalar_one_or_none() is None


async def test_delete_is_refused_for_a_regular_user(
    client, logged_in, stored_user, db_session
):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.delete(
        f"/delete_user/{stored_user.id}",
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" not in response.headers
    assert "Not authorized" in response.text
    db_session.expire_all()
    found = await db_session.execute(select(User).where(User.email == EMAIL))
    assert found.scalar_one_or_none() is not None


async def test_superuser_cannot_delete_their_own_account(
    client, logged_in, stored_user, db_session
):
    token = await csrf_token_from(client)
    logged_in.id = stored_user.id
    response = await client.delete(
        f"/delete_user/{stored_user.id}",
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" not in response.headers
    assert "cannot delete your own account" in response.text
    db_session.expire_all()
    found = await db_session.execute(select(User).where(User.email == EMAIL))
    assert found.scalar_one_or_none() is not None


async def test_user_profile_markup_is_escaped_in_the_list(
    client, logged_in, stored_user, db_session
):
    payload = "<script>alert(1)</script>"
    stored_user.profile.first_name = payload
    await db_session.commit()
    response = await client.get("/user", headers=HX)
    assert payload not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


async def test_profile_update_message_names_the_user(
    client, logged_in, stored_user, db_session
):
    role = Role(role_name="pytest-update-role")
    db_session.add(role)
    await db_session.commit()
    try:
        token = await csrf_token_from(client)
        response = await client.put(
            f"/post_update_user/{stored_user.id}",
            headers={**HX, "X-CSRF-Token": token},
            data={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "gender": "female",
                "phone": "+44 1234 567890",
                "role_id": str(role.id),
            },
        )
        assert response.status_code == 200, response.text
        alert = json.loads(response.headers["HX-Trigger"])["showAlert"]
        assert alert["message"] == "Profile for Ada Lovelace updated successfully."
    finally:
        await db_session.execute(
            update(User).where(User.id == stored_user.id).values(role_id=None)
        )
        await db_session.execute(delete(Role).where(Role.id == role.id))
        await db_session.commit()


def phone_pattern():
    template = Path("app/templates/partials/user/edit_user.html").read_text()
    return re.search(r'id="phone"[^>]*? pattern="([^"]+)"', template).group(1)


@pytest.mark.parametrize(
    "number",
    [
        "(123) 456-7890",
        "01234 567890",
        "0412 345 678",
        "+44 1234 567890",
        "123-456-7890",
    ],
)
def test_phone_pattern_accepts_the_placeholder_examples(number):
    assert re.fullmatch(phone_pattern(), number)


@pytest.mark.parametrize("number", ["abc", "12", "1234567890123456"])
def test_phone_pattern_rejects_bad_numbers(number):
    assert not re.fullmatch(phone_pattern(), number)


def test_phone_input_limits_its_length():
    template = Path("app/templates/partials/user/edit_user.html").read_text()
    assert re.search(r'id="phone"[^>]*? maxlength="15"', template)
