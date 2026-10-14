"""CSRF tokens: one cookie per browser, reused by every page and tab."""

import re
import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi_csrf_protect import CsrfProtect
from httpx import ASGITransport, AsyncClient
from itsdangerous import TimestampSigner, URLSafeTimedSerializer
from sqlalchemy import delete, select
from starlette.requests import Request
from starlette.responses import Response

from app.app import app
from app.database.security import current_active_user
from app.models.groups import Group
from app.models.users import Role, User, UserProfile
from app.routes.view.csrf import csrf_token_for, set_csrf_cookie

from .conftest import TEST_ROLE_PREFIX

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
ROLE_NAME = TEST_ROLE_PREFIX + "csrf-role"
NEW_ROLE_NAME = TEST_ROLE_PREFIX + "csrf-new-role"
GROUP_NAME = "pytest-csrf-group"
USER_EMAIL = "pytest-csrf-user@example.com"
# What handle_error shows when the check fails: in the body of a form, in the
# HX-Trigger alert of a delete
REFUSAL = ("Your session has expired",)


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
async def rows(db_session):
    """A role, a group and a user with a profile; all deleted afterwards."""
    role = Role(role_name=ROLE_NAME, role_desc="csrf tests")
    group = Group(group_name=GROUP_NAME, group_desc="csrf tests")
    profile = UserProfile(first_name="Ada", last_name="Lovelace")
    db_session.add_all([role, group, profile])
    await db_session.flush()
    user = User(
        email=USER_EMAIL,
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        is_verified=False,
        profile_id=profile.id,
    )
    db_session.add(user)
    await db_session.commit()
    ids = SimpleNamespace(
        role=role.id, group=group.id, user=user.id, profile=profile.id
    )
    yield ids
    await db_session.rollback()
    await db_session.execute(delete(User).where(User.id == ids.user))
    await db_session.execute(delete(UserProfile).where(UserProfile.id == ids.profile))
    await db_session.execute(delete(Group).where(Group.group_name.like("pytest-%")))
    await db_session.commit()


def token_in(page):
    found = re.search(r'"X-CSRF-Token":\s*"([^"]+)"', page.text)
    assert found, "the page renders no CSRF token"
    return found.group(1)


def refused(response):
    shown = response.text + response.headers.get("HX-Trigger", "")
    return response.status_code == 403 and any(text in shown for text in REFUSAL)


# Every form opened directly by its URL, as a full page: the URL, and the write
# that form makes (method, URL, form fields)
FORMS = {
    "role-add": (
        "/get_create_roles",
        (
            "post",
            "/post_create_roles",
            {"role_name": NEW_ROLE_NAME, "role_desc": "valid text"},
        ),
    ),
    "role-edit": (
        "/get_role/{role}",
        (
            "put",
            "/post_update_role/{role}",
            {"role_name": ROLE_NAME, "role_desc": "valid text"},
        ),
    ),
    "group-add": (
        "/get_create_group",
        (
            "post",
            "/post_create_group",
            {"group_name": GROUP_NAME + "-new", "group_desc": "valid text"},
        ),
    ),
    "group-edit": (
        "/get_group/{group}",
        (
            "put",
            "/post_update_group/{group}",
            {"group_name": GROUP_NAME, "group_desc": "valid text"},
        ),
    ),
    "user-edit": (
        "/get_user/{user}",
        ("put", "/post_update_user/{user}", {"first_name": "Ada"}),
    ),
    "upload": ("/uploads", ("delete", "/delete/nothing.txt", None)),
}


@pytest.mark.parametrize("name", FORMS)
async def test_form_opened_by_url_renders_a_token_the_write_accepts(
    client, logged_in, rows, name
):
    page_url, (method, write_url, data) = FORMS[name]
    ids = vars(rows)
    page = await client.get(page_url.format(**ids))  # no HX-Request, no header
    assert page.status_code == 200
    assert "<nav" in page.text
    token = token_in(page)
    assert token
    response = await client.request(
        method,
        write_url.format(**ids),
        data=data,
        headers={**HX, "X-CSRF-Token": token},
    )
    assert not refused(response)
    if name == "role-add":
        assert "HX-Location" in response.headers


async def test_write_with_a_wrong_token_is_refused_after_a_direct_open(
    client, logged_in, rows
):
    await client.get("/get_create_roles")
    response = await client.post(
        "/post_create_roles",
        data={"role_name": NEW_ROLE_NAME, "role_desc": "valid text"},
        headers={**HX, "X-CSRF-Token": "not-the-token"},
    )
    assert refused(response)
    assert "HX-Location" not in response.headers


async def test_a_second_tab_does_not_break_the_first(
    client, logged_in, rows, db_session
):
    first = token_in(await client.get("/role", headers=HX))
    await client.get("/role", headers=HX)  # the second tab
    response = await client.delete(
        f"/delete_role/{rows.role}", headers={**HX, "X-CSRF-Token": first}
    )
    assert "HX-Location" in response.headers
    db_session.expire_all()
    found = await db_session.execute(select(Role).where(Role.id == rows.role))
    assert found.scalar_one_or_none() is None


async def test_a_write_does_not_rotate_the_cookie(client, logged_in, rows):
    token = token_in(await client.get("/role", headers=HX))
    cookie = client.cookies["fastapi-csrf-token"]
    response = await client.delete(
        f"/delete_role/{rows.role}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "HX-Location" in response.headers
    assert "set-cookie" not in response.headers
    assert client.cookies["fastapi-csrf-token"] == cookie


async def test_a_failed_write_answers_with_a_token_that_works(client, logged_in, rows):
    # No cookie at all: the refusal renders the form with a new pair
    response = await client.post(
        "/post_create_roles", data={"role_name": "x"}, headers=HX
    )
    assert refused(response)
    token = token_in(response)
    retry = await client.post(
        "/post_create_roles",
        data={"role_name": NEW_ROLE_NAME, "role_desc": "valid text"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" in retry.headers


# The helper


@pytest.fixture
def csrf_protect():
    return CsrfProtect()


def request_with(cookie_value=None):
    headers = []
    if cookie_value is not None:
        headers.append((b"cookie", f"fastapi-csrf-token={cookie_value}".encode()))
    return Request({"type": "http", "headers": headers})


def signed_aged(csrf_protect, token, age):
    """What the library signs, as if it had been signed `age` seconds ago."""

    class AgedSigner(TimestampSigner):
        def get_timestamp(self):
            return int(time.time()) - age

    serializer = URLSafeTimedSerializer(
        csrf_protect._secret_key, salt="fastapi-csrf-token", signer=AgedSigner
    )
    return serializer.dumps(token)


async def test_helper_reuses_a_valid_cookie(csrf_protect):
    token, signed = csrf_protect.generate_csrf_tokens()
    got, new = csrf_token_for(request_with(signed), csrf_protect)
    assert got == token
    assert new is None
    response = Response()
    set_csrf_cookie(csrf_protect, response, new)
    assert "set-cookie" not in response.headers


async def test_helper_reuses_a_cookie_just_under_half_its_lifetime(csrf_protect):
    half = csrf_protect._max_age // 2
    signed = signed_aged(csrf_protect, "a" * 40, half - 60)
    assert csrf_token_for(request_with(signed), csrf_protect) == ("a" * 40, None)


@pytest.mark.parametrize("case", ["none", "tampered", "expired", "past-half", "junk"])
async def test_helper_makes_a_new_pair_otherwise(csrf_protect, case):
    max_age = csrf_protect._max_age
    old_token = "b" * 40
    cookie = {
        "none": None,
        "tampered": signed_aged(csrf_protect, old_token, 0)[:-3] + "xyz",
        "expired": signed_aged(csrf_protect, old_token, max_age + 60),
        "past-half": signed_aged(csrf_protect, old_token, max_age // 2 + 60),
        "junk": "not-a-signed-value",
    }[case]
    token, new = csrf_token_for(request_with(cookie), csrf_protect)
    assert token != old_token
    assert new and new != cookie
    response = Response()
    set_csrf_cookie(csrf_protect, response, new)
    assert "fastapi-csrf-token=" in response.headers["set-cookie"]


async def test_helper_token_passes_validate_csrf_with_its_cookie(csrf_protect):
    _, signed = csrf_protect.generate_csrf_tokens()
    token, new = csrf_token_for(request_with(signed), csrf_protect)
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"cookie", f"fastapi-csrf-token={signed}".encode()),
                (b"x-csrf-token", token.encode()),
            ],
        }
    )
    await csrf_protect.validate_csrf(request)
