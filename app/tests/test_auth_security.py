import re
import uuid

import pytest
from fastapi_users.password import PasswordHelper
from httpx import ASGITransport, AsyncClient
from loguru import logger
from sqlalchemy import delete

from app.app import app
from app.core.csrf_settings import CsrfSettings, crsf_settings
from app.database.security import (
    SECRET,
    build_cookie_transport,
    get_jwt_strategy,
)
from app.models.users import User

pytestmark = pytest.mark.anyio

COOKIE = "fastapiusersauth"
EMAIL_PREFIX = "pytest-authsec-"
PASSWORD = "a-long-enough-password"
CSRF_MESSAGE = {"detail": "CSRF token missing or invalid"}


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as c:
        yield c


async def _add_user(session, name, superuser=False):
    user = User(
        email=f"{EMAIL_PREFIX}{name}@example.com",
        hashed_password=PasswordHelper().hash(PASSWORD),
        is_active=True,
        is_superuser=superuser,
        is_verified=False,
    )
    session.add(user)
    await session.commit()
    return user


@pytest.fixture
async def users(db_session):
    async def purge():
        await db_session.execute(
            delete(User).where(User.email.like(f"{EMAIL_PREFIX}%"))
        )
        await db_session.commit()

    await purge()
    admin = await _add_user(db_session, "admin", superuser=True)
    other = await _add_user(db_session, "other")
    admin_id, other_id = admin.id, other.id
    yield {
        "admin": admin.email,
        "admin_id": admin_id,
        "other": other.email,
        "other_id": other_id,
    }
    db_session.expire_all()
    await purge()


async def csrf_headers(client):
    """A CSRF pair as the login page hands it out: cookie in the jar, token returned."""
    page = await client.get("/login")
    token = re.search(r'data-csrf-token="([^"]+)"', page.text).group(1)
    return {"X-CSRF-Token": token}


def credentials(email, password=PASSWORD):
    return {"username": email, "password": password}


async def login(client, email, password=PASSWORD):
    headers = await csrf_headers(client)
    response = await client.post(
        "/auth/jwt/login", data=credentials(email, password), headers=headers
    )
    return response, headers


# 1. verify_jwt behind GET /


@pytest.mark.parametrize("value", ["garbage", "a.b.c", ""])
async def test_index_sends_a_garbage_cookie_to_login(client, value):
    client.cookies.set(COOKIE, value)
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


async def test_index_sends_a_real_login_cookie_to_the_dashboard(client, users):
    response, _ = await login(client, users["other"])
    assert response.status_code == 204
    assert COOKIE in client.cookies
    index = await client.get("/", follow_redirects=False)
    assert index.status_code == 302
    assert index.headers["location"] == "/dashboard"


async def test_index_refuses_an_expired_and_a_wrongly_signed_token(client, users):
    from fastapi_users.authentication import JWTStrategy

    user = User(id=users["other_id"], email=users["other"])
    for strategy in (
        JWTStrategy(secret=SECRET, lifetime_seconds=-60),
        JWTStrategy(secret="another-secret-of-thirty-two-chars!!", lifetime_seconds=60),
    ):
        client.cookies.set(COOKIE, await strategy.write_token(user))
        response = await client.get("/", follow_redirects=False)
        assert response.headers["location"] == "/login"
    # The same user with the right secret and lifetime is accepted
    client.cookies.set(COOKIE, await get_jwt_strategy().write_token(user))
    response = await client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/dashboard"


async def test_index_refuses_a_token_for_an_unknown_user(client):
    user = User(id=uuid.uuid4(), email="nobody@example.com")
    client.cookies.set(COOKIE, await get_jwt_strategy().write_token(user))
    response = await client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/login"


async def _token_for(session, name, active, **claims):
    from fastapi_users.jwt import generate_jwt

    user = await _add_user(session, name)
    user.is_active = active
    await session.commit()
    data = {"sub": str(user.id), "aud": "fastapi-users:auth", **claims}
    return generate_jwt(data, SECRET, 60)


async def test_index_refuses_a_valid_token_of_an_inactive_user(
    client, users, db_session
):
    token = await _token_for(db_session, "inactive", active=False)
    client.cookies.set(COOKIE, token)
    response = await client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/login"
    active = await _token_for(db_session, "active", active=True)
    client.cookies.set(COOKIE, active)
    response = await client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/dashboard"


@pytest.mark.parametrize("audience", ["fastapi-users:reset", "fastapi-users:verify"])
async def test_index_refuses_a_token_with_another_audience(
    client, users, db_session, audience
):
    token = await _token_for(db_session, "aud", active=True, aud=audience)
    client.cookies.set(COOKIE, token)
    response = await client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/login"


# 3. cookie flags come from the settings


def test_samesite_none_without_secure_is_refused_by_the_csrf_library():
    # fastapi-csrf-protect checks this when it loads the config (the first CSRF
    # request), so the app never runs with a cookie browsers would drop
    from fastapi_csrf_protect.load_config import LoadConfig
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="cookie_secure"):
        LoadConfig(secret_key="x" * 32, cookie_samesite="none", cookie_secure=False)
    LoadConfig(secret_key="x" * 32, cookie_samesite="none", cookie_secure=True)


def test_samesite_is_restricted_to_lax_strict_none():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CsrfSettings(CSRF_SECRET_KEY="x" * 32, COOKIE_SAMESITE="Lax", COOKIE_SECURE=1)
    with pytest.raises(ValidationError):
        CsrfSettings(CSRF_SECRET_KEY="x" * 32, COOKIE_SAMESITE="", COOKIE_SECURE=1)


@pytest.mark.parametrize("secure", [True, False])
@pytest.mark.parametrize("samesite", ["lax", "strict", "none"])
def test_cookie_transport_takes_secure_and_samesite_from_settings(secure, samesite):
    settings = CsrfSettings(
        CSRF_SECRET_KEY="x" * 32, COOKIE_SAMESITE=samesite, COOKIE_SECURE=secure
    )
    transport = build_cookie_transport(settings)
    assert transport.cookie_secure is secure
    assert transport.cookie_samesite == samesite
    assert transport.cookie_httponly is True


async def test_login_cookie_follows_cookie_secure(client, users):
    response, _ = await login(client, users["other"])
    cookie = next(
        h for h in response.headers.get_list("set-cookie") if h.startswith(COOKIE)
    )
    assert ("secure" in cookie.lower()) is crsf_settings.cookie_secure
    assert "httponly" in cookie.lower()


# Log out is exempt from CSRF: the shell posts it with no token


async def test_logout_without_a_token_is_204_and_clears_the_cookie(client, users):
    await login(client, users["other"])
    assert COOKIE in client.cookies
    # Exactly what shell.js sends: a bare POST, no CSRF header
    response = await client.post("/auth/jwt/logout")
    assert response.status_code == 204
    cleared = next(
        h for h in response.headers.get_list("set-cookie") if h.startswith(COOKIE)
    )
    assert 'Max-Age=0' in cleared or "01 Jan 1970" in cleared
    assert COOKIE not in client.cookies


async def test_the_logout_exemption_does_not_cover_login(client, users):
    response = await client.post("/auth/jwt/login", data=credentials(users["other"]))
    assert response.status_code == 403


def test_the_exempt_route_name_is_the_library_logout_route():
    from app.app import auth_backend, fastapi_users
    from app.database.security import LOGOUT_ROUTE_NAME

    routes = fastapi_users.get_auth_router(auth_backend).routes
    assert {r.name: r.path for r in routes}[LOGOUT_ROUTE_NAME] == "/logout"


# 4. CSRF on login


async def test_login_without_csrf_header_and_cookie_is_403(client, users):
    response = await client.post("/auth/jwt/login", data=credentials(users["other"]))
    assert response.status_code == 403
    assert response.json() == CSRF_MESSAGE
    assert COOKIE not in response.headers.get("set-cookie", "")


async def test_login_with_header_but_no_cookie_is_403(client, users):
    other = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    async with other:
        headers = await csrf_headers(other)
    response = await client.post(
        "/auth/jwt/login", data=credentials(users["other"]), headers=headers
    )
    assert response.status_code == 403
    assert COOKIE not in response.headers.get("set-cookie", "")


async def test_login_with_a_mismatched_pair_is_403(client, users):
    await csrf_headers(client)
    stranger = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    async with stranger:
        wrong = await csrf_headers(stranger)
    response = await client.post(
        "/auth/jwt/login", data=credentials(users["other"]), headers=wrong
    )
    assert response.status_code == 403
    assert response.json() == CSRF_MESSAGE
    assert COOKIE not in response.headers.get("set-cookie", "")


async def test_login_valid_pair_good_credentials_is_204_with_cookie(client, users):
    response, _ = await login(client, users["other"])
    assert response.status_code == 204
    assert COOKIE in response.headers["set-cookie"]


async def test_login_valid_pair_bad_credentials_is_400(client, users):
    response, _ = await login(client, users["other"], "wrong-password-value")
    assert response.status_code == 400
    assert COOKIE not in response.headers.get("set-cookie", "")


async def test_csrf_is_checked_before_the_credentials(client, users):
    response = await client.post(
        "/auth/jwt/login", data=credentials(users["other"], "wrong-password-value")
    )
    assert response.status_code == 403


async def test_csrf_error_answer_never_carries_the_token(client):
    headers = {"X-CSRF-Token": "sentinel-token-5d2c"}
    response = await client.post(
        "/auth/jwt/login", data=credentials("a@example.com"), headers=headers
    )
    assert response.status_code == 403
    assert "sentinel-token-5d2c" not in response.text


# 5. CSRF on register, reset password and verify

AUTH_POSTS = [
    (
        "/auth/register",
        {"email": f"{EMAIL_PREFIX}new@example.com", "password": PASSWORD},
    ),
    ("/auth/forgot-password", {"email": "nobody@example.com"}),
    ("/auth/reset-password", {"token": "x", "password": PASSWORD}),
    ("/auth/request-verify-token", {"email": "nobody@example.com"}),
    ("/auth/verify", {"token": "x"}),
]


@pytest.mark.parametrize("path,body", AUTH_POSTS)
async def test_auth_posts_refuse_a_missing_or_empty_token(client, users, path, body):
    assert (await client.post(path, json=body)).status_code == 403
    empty = await client.post(path, json=body, headers={"X-CSRF-Token": ""})
    assert empty.status_code == 403


async def test_register_works_with_the_token_the_page_sends(client, users):
    page = await client.get("/register")
    token = re.search(r'data-csrf-token="([^"]+)"', page.text).group(1)
    response = await client.post(
        "/auth/register",
        json={"email": f"{EMAIL_PREFIX}new@example.com", "password": PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 201
    again = await client.post(
        "/auth/register",
        json={"email": f"{EMAIL_PREFIX}new@example.com", "password": PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert again.status_code == 400


def component_body(script, name):
    """The text of one Alpine.data(name, ...) block, up to the next component."""
    start = script.index(f'Alpine.data("{name}"')
    end = script.find("Alpine.data(", start + 1)
    return script[start:] if end == -1 else script[start:end]


def register_fetch_sends_token(script):
    body = component_body(script, "register")
    call = body[body.index('fetch("/auth/register"') :]
    return "X-CSRF-Token" in call.split("body:")[0]


def test_register_script_sends_the_token_header():
    from pathlib import Path

    assert register_fetch_sends_token(Path("app/static/js/components.js").read_text())


def test_register_script_check_flags_a_header_only_in_another_component():
    flagged = (
        'Alpine.data("register", () => ({ go() { fetch("/auth/register", '
        '{ headers: {}, body: x }); } }));\n'
        'Alpine.data("login", () => ({ go() { fetch("/auth/jwt/login", '
        '{ headers: { "X-CSRF-Token": t } }); } }));'
    )
    assert not register_fetch_sends_token(flagged)
    ok = flagged.replace("headers: {},", 'headers: { "X-CSRF-Token": t },')
    assert register_fetch_sends_token(ok)
    # The word in a comment far from the fetch call does not count
    assert not register_fetch_sends_token(
        '// X-CSRF-Token\nAlpine.data("register", () => ({ go() { '
        'fetch("/auth/register", { headers: {}, body: x }); } }));'
    )


# 6. fastapi-users /users router


async def test_users_router_delete_needs_csrf(client, users):
    await login(client, users["admin"])
    response = await client.delete(f"/users/{users['other_id']}")
    assert response.status_code == 403


@pytest.mark.parametrize("form", ["canonical", "upper", "no_hyphens"])
async def test_users_router_refuses_a_self_delete(client, users, db_session, form):
    _, headers = await login(client, users["admin"])
    own = users["admin_id"]
    spelled = {"canonical": str(own), "upper": str(own).upper(), "no_hyphens": own.hex}
    response = await client.delete(f"/users/{spelled[form]}", headers=headers)
    assert response.status_code == 400
    assert (await client.get("/users/me")).status_code == 200
    assert await db_session.get(User, own) is not None


async def test_users_router_leaves_a_non_uuid_to_the_library(client, users):
    _, headers = await login(client, users["admin"])
    lines: list[str] = []
    sink = logger.add(lines.append, level="ERROR")
    try:
        response = await client.delete("/users/not-a-uuid", headers=headers)
    finally:
        logger.remove(sink)
    # The library answers 404 (an unparseable id); the app's handler shows 400.
    # Our own guard would log "cannot delete your own account" instead.
    assert response.status_code == 400
    assert "Not Found : 404" in "".join(lines)
    assert "own account" not in "".join(lines)


async def test_users_router_still_deletes_another_user_with_csrf(client, users):
    _, headers = await login(client, users["admin"])
    response = await client.delete(f"/users/{users['other_id']}", headers=headers)
    assert response.status_code == 204


@pytest.mark.parametrize("path", ["/users/me", f"/users/{uuid.uuid4()}"])
async def test_users_router_patch_needs_csrf(client, users, path):
    await login(client, users["admin"])
    response = await client.patch(path, json={})
    assert response.status_code == 403


async def test_users_router_reads_need_no_csrf(client, users):
    await login(client, users["admin"])
    assert (await client.get("/users/me")).status_code == 200
    assert (await client.get(f"/users/{users['other_id']}")).status_code == 200
