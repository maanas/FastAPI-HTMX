"""Error answers: the status, the message the user sees, what htmx swaps, and the URL
after a failed write. The per-route refusals are asserted next to their routes in the
test_*_view.py files; this file holds what is shared."""

import json
import re
import sqlite3
import uuid
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi_csrf_protect.exceptions import CsrfProtectError
from httpx import ASGITransport, AsyncClient
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.app import app
from app.database.security import current_active_user
from app.routes.view import group as group_routes
from app.routes.view import role as role_routes
from app.routes.view import user as user_routes
from app.routes.view.errors import (
    CSRF_MESSAGE,
    ERROR_RENDERED_HEADER,
    UNEXPECTED_MESSAGE,
    alert_error,
    error_status_and_messages,
)
from app.schema.users import RoleCreate

from .conftest import TEST_ROLE_PREFIX
from .error_asserts import alert_message

pytestmark = pytest.mark.anyio

APP = Path(__file__).resolve().parents[1]
TEMPLATES = APP / "templates"
HX = {"HX-Request": "true"}
# Text an exception carries that no answer may show
LEAK = "SELECT secret FROM users WHERE password = 'hunter2'"


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


async def csrf_token_from(client):
    page = await client.get("/role", headers=HX)
    return re.search(r'"X-CSRF-Token":\s*"([^"]+)"', page.text).group(1)


def invalid_role():
    with pytest.raises(ValidationError) as caught:
        RoleCreate(role_name="x", role_desc="valid description")
    return caught.value


# --- the status and the message per kind of error


def test_status_and_message_per_kind_of_error():
    status, messages = error_status_and_messages(invalid_role())
    assert status == 422
    assert messages == ["role_name: String should have at least 3 characters"]

    assert error_status_and_messages(HTTPException(404, "File not found")) == (
        404,
        ["File not found"],
    )
    assert error_status_and_messages(HTTPException(409, "Name taken")) == (
        409,
        ["Name taken"],
    )
    # A detail that is not text is not shown
    assert error_status_and_messages(HTTPException(400, {"a": LEAK})) == (
        400,
        [UNEXPECTED_MESSAGE],
    )
    assert error_status_and_messages(CsrfProtectError(400, LEAK)) == (
        403,
        [CSRF_MESSAGE],
    )
    assert error_status_and_messages(RuntimeError(LEAK)) == (500, [UNEXPECTED_MESSAGE])


def test_validation_messages_are_readable_field_messages():
    _, messages = error_status_and_messages(invalid_role())
    for message in messages:
        assert not re.search(r"[(),']", message.split(": ")[0]), message


async def test_validation_error_answers_422_with_the_field_message(client, logged_in):
    token = await csrf_token_from(client)
    response = await client.post(
        "/post_create_roles",
        data={"role_name": "x", "role_desc": "valid description"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 422
    assert response.headers[ERROR_RENDERED_HEADER] == "1"
    assert "role_name: String should have at least 3 characters" in response.text
    assert "(" not in response.text.split("role_name")[1].split("<")[0]


async def test_a_missing_row_answers_404_on_each_edit_route(client, logged_in):
    unknown = uuid.uuid4()
    for url in (
        f"/get_role/{unknown}",
        f"/get_group/{unknown}",
        f"/get_user/{unknown}",
    ):
        for headers in ({}, HX):
            response = await client.get(url, headers=headers)
            assert response.status_code == 404, url
            assert "not found" in response.text


async def test_a_bad_date_is_a_422_not_a_crash(client, logged_in):
    token = await csrf_token_from(client)
    response = await client.put(
        f"/post_update_user/{uuid.uuid4()}",
        data={"first_name": "Ada", "dob": "31/12/1999", "role_id": str(uuid.uuid4())},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 422
    assert "not valid" in response.text


# --- no raw exception text


async def test_a_csrf_failure_shows_only_the_fixed_message(client, logged_in):
    for method, url in (
        ("post", "/post_create_roles"),
        ("put", f"/post_update_role/{uuid.uuid4()}"),
        ("post", f"/post_group_user_link/{uuid.uuid4()}"),
    ):
        response = await getattr(client, method)(url, data={}, headers=HX)
        assert response.status_code == 403, url
        assert CSRF_MESSAGE in response.text
        for raw in ("Missing Cookie", "CSRF signatures", "CSRF token", "Bad headers"):
            assert raw not in response.text, url


@pytest.mark.parametrize(
    "target, name, method, url",
    [
        (role_routes.role_crud, "create", "post", "/post_create_roles"),
        (group_routes.group_crud, "create", "post", "/post_create_group"),
        (
            user_routes.user_crud,
            "read_by_primary_key",
            "put",
            "/post_update_user/00000000-0000-0000-0000-000000000001",
        ),
    ],
)
async def test_an_unexpected_exception_is_logged_and_never_shown(
    client, logged_in, monkeypatch, target, name, method, url
):
    async def boom(*args, **kwargs):
        raise RuntimeError(LEAK)

    token = await csrf_token_from(client)
    monkeypatch.setattr(target, name, boom)
    form = {
        "role_name": TEST_ROLE_PREFIX + "boom-role",
        "role_desc": "valid description",
        "group_name": "pytest-boom-group",
        "group_desc": "valid description",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "gender": "female",
        "role_id": str(uuid.uuid4()),
    }
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="ERROR")
    try:
        response = await getattr(client, method)(
            url, data=form, headers={**HX, "X-CSRF-Token": token}
        )
    finally:
        logger.remove(sink)
    assert response.status_code == 500
    assert response.headers[ERROR_RENDERED_HEADER] == "1"
    assert UNEXPECTED_MESSAGE in response.text
    assert LEAK not in response.text
    assert "RuntimeError" not in response.text
    # The traceback is in the log
    log = "".join(lines)
    assert "RuntimeError" in log and LEAK in log
    assert "in boom" in log  # the frame of the raising function
    assert "File " in log


# A value only a route's local variables hold, and one only a database error carries
LOCAL_VALUE = "distinctive-local-value-4711"
DB_VALUE = "distinctive-db-parameter-9082"


def database_error():
    return IntegrityError(
        "INSERT INTO role (role_name) VALUES (?)",
        {"role_name": DB_VALUE},
        sqlite3.IntegrityError(f"UNIQUE constraint failed: {DB_VALUE}"),
    )


async def post_role_and_capture(client, monkeypatch, error):
    async def boom(*args, **kwargs):
        raise error

    token = await csrf_token_from(client)
    monkeypatch.setattr(role_routes.role_crud, "create", boom)
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
    try:
        response = await client.post(
            "/post_create_roles",
            data={"role_name": TEST_ROLE_PREFIX + "log-role", "role_desc": LOCAL_VALUE},
            headers={**HX, "X-CSRF-Token": token},
        )
    finally:
        logger.remove(sink)
    return response, "".join(lines)


async def test_a_local_variable_of_the_route_is_not_logged(
    client, logged_in, monkeypatch
):
    # role_desc is held in the route's locals while the crud call raises
    response, log = await post_role_and_capture(
        client, monkeypatch, RuntimeError("boom")
    )
    assert response.status_code == 500
    assert "RuntimeError" in log
    assert LOCAL_VALUE not in log
    assert "X-CSRF-Token" not in log


async def test_a_database_error_logs_its_type_but_not_statement_or_values(
    client, logged_in, monkeypatch
):
    response, log = await post_role_and_capture(client, monkeypatch, database_error())
    assert response.status_code == 500
    assert "IntegrityError (driver: IntegrityError)" in log
    for leaked in (DB_VALUE, "INSERT INTO", "UNIQUE constraint", LOCAL_VALUE):
        assert leaked not in log
        if leaked != LOCAL_VALUE:
            assert leaked not in response.text
    # The typed description comes back once, in its input, not in the alert text
    assert response.text.count(LOCAL_VALUE) == 1
    assert f'value="{LOCAL_VALUE}"' in response.text


async def test_a_database_error_in_the_exception_chain_is_not_logged(
    client, logged_in, monkeypatch
):
    try:
        try:
            raise database_error()
        except IntegrityError as db_error:
            raise RuntimeError("could not save the role") from db_error
    except RuntimeError as wrapped:
        error = wrapped
    response, log = await post_role_and_capture(client, monkeypatch, error)
    assert response.status_code == 500
    assert "RuntimeError: could not save the role" in log
    assert "IntegrityError" in log
    for leaked in (DB_VALUE, "INSERT INTO", "UNIQUE constraint"):
        assert leaked not in log


def test_the_context_chain_is_followed_too():
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="ERROR")
    try:
        try:
            raise database_error()
        except IntegrityError:
            raise ValueError("while handling")  # chained through __context__
    except ValueError as error:
        error_status_and_messages(error)
    finally:
        logger.remove(sink)
    log = "".join(lines)
    assert "IntegrityError" in log and DB_VALUE not in log


async def test_a_failed_delete_alert_never_shows_the_exception(
    client, logged_in, monkeypatch
):
    async def boom(*args, **kwargs):
        raise RuntimeError(LEAK)

    token = await csrf_token_from(client)
    monkeypatch.setattr(role_routes.role_crud, "read_by_primary_key", boom)
    response = await client.delete(
        f"/delete_role/{uuid.uuid4()}", headers={**HX, "X-CSRF-Token": token}
    )
    assert response.status_code == 500
    assert alert_message(response) == UNEXPECTED_MESSAGE
    assert LEAK not in response.headers["HX-Trigger"]


# --- what htmx may swap


async def test_a_rendered_error_carries_the_marker_and_others_do_not(client, logged_in):
    rendered = await client.get("/get_role/" + str(uuid.uuid4()), headers=HX)
    assert rendered.status_code == 404
    assert rendered.headers[ERROR_RENDERED_HEADER] == "1"

    # The JSON 403 of csrf_error_handler, and a 404 for a path with no route
    refused = await client.post(
        "/auth/jwt/login", data={"username": "a@example.com", "password": "x"}
    )
    assert refused.status_code == 403
    assert refused.headers["content-type"].startswith("application/json")
    assert ERROR_RENDERED_HEADER not in refused.headers
    missing = await client.get("/no-such-page", headers=HX)
    assert missing.status_code >= 400
    assert ERROR_RENDERED_HEADER not in missing.headers

    # An alert answer is never swapped
    alert = alert_error(HTTPException(404, "Gone"), "role-page")
    assert ERROR_RENDERED_HEADER not in alert.headers


def test_the_shell_swaps_only_answers_with_the_marker():
    shell = (APP / "static" / "js" / "shell.js").read_text()
    assert 'addEventListener("htmx:beforeSwap"' in shell
    assert f'getResponseHeader("{ERROR_RENDERED_HEADER}") === "1"' in shell
    assert "event.detail.shouldSwap = true" in shell
    # The marker is the mechanism, not a status list for every 4xx
    meta = re.search(r'name="htmx-config" content=\'([^\']*)\'', base_html()).group(1)
    assert "responseHandling" not in json.loads(meta)


def base_html():
    return (TEMPLATES / "base" / "base.html").read_text()


def test_list_alerts_have_an_error_type_and_every_list_shows_it():
    components = (APP / "static" / "js" / "components.js").read_text()
    assert "isError: false" in components
    assert '"isError"' in components  # reset by watchAlerts
    assert 'alertData.type === "error"' in components
    for name in (
        "partials/role/role_list.html",
        "partials/group/groups.html",
        "partials/user/user_list.html",
        "partials/upload/upload.html",
    ):
        text = (TEMPLATES / name).read_text()
        assert 'x-show="isError"' in text, name
        assert 'role="alert"' in text.split('x-show="isError"')[1].split(">")[0]


# --- the address bar after a failed write

WRITE_ATTRS = ("hx-post", "hx-put", "hx-patch", "hx-delete")
URL_ATTRS = ("hx-push-url", "hx-replace-url")
# A known broken template that is out of this step, see TODO.md
SKIPPED = {"partials/user/add_user.html"}


class _WriteScanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        names = {name.lower().removeprefix("data-") for name, _ in attrs}
        if names & set(WRITE_ATTRS) and names & set(URL_ATTRS):
            self.found.append((tag, self.getpos()[0]))

    handle_startendtag = handle_starttag


def writes_that_set_the_url(text):
    """(tag, line) of every element that sends a write and also sets the address bar."""
    scanner = _WriteScanner()
    scanner.feed(text)
    scanner.close()
    return scanner.found


def test_the_write_guard_flags_every_attribute_form():
    for write in WRITE_ATTRS:
        for url in URL_ATTRS:
            assert writes_that_set_the_url(f'<form {write}="/x" {url}="true">')
            assert writes_that_set_the_url(
                f'<form data-{write}="/x" data-{url}="true">'
            )
    # A GET navigation may push its URL; words inside a string are not attributes
    assert not writes_that_set_the_url('<a hx-get="/x" hx-push-url="true">Go</a>')
    assert not writes_that_set_the_url('<form hx-post="/x" class="hx-push-url">')
    assert not writes_that_set_the_url('<p title="hx-post hx-push-url">hx-push-url</p>')


def test_no_write_form_puts_its_url_in_the_address_bar():
    # A failed write is answered at its POST-only URL: pushing it makes a reload a 405
    for path in sorted(TEMPLATES.rglob("*.html")):
        name = path.relative_to(TEMPLATES).as_posix()
        if name in SKIPPED:
            continue
        assert not writes_that_set_the_url(path.read_text()), name


async def test_a_failed_write_answer_pushes_no_url(client, logged_in):
    token = await csrf_token_from(client)
    for path, data in (
        ("/post_create_roles", {"role_name": "x"}),
        ("/post_create_group", {"group_name": "x"}),
    ):
        response = await client.post(
            path, data=data, headers={**HX, "X-CSRF-Token": token}
        )
        assert response.status_code == 422, path
        assert "HX-Push-Url" not in response.headers
        assert "HX-Location" not in response.headers
        assert "HX-Replace-Url" not in response.headers
    # The forms themselves, as the failed post is swapped over them
    for url in ("/get_create_roles", "/get_create_group"):
        form = (await client.get(url, headers=HX)).text
        assert "hx-push-url" not in form


# --- a refused delete leaves the list


async def test_a_refused_delete_alerts_and_swaps_nothing(client, logged_in):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    for url, source in (
        (f"/delete_role/{uuid.uuid4()}", "role-page"),
        (f"/delete_group/{uuid.uuid4()}", "group-page"),
        (f"/delete_user/{uuid.uuid4()}", "user-page"),
        ("/delete/whatever.txt", "upload-page"),
    ):
        response = await client.delete(url, headers={**HX, "X-CSRF-Token": token})
        assert response.status_code == 403, url
        assert "Not authorized" in alert_message(response)
        alert = json.loads(response.headers["HX-Trigger"])["showAlert"]
        assert alert["source"] == source


async def test_a_delete_without_htmx_still_gets_a_page(client, logged_in):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.delete(
        f"/delete_role/{uuid.uuid4()}", headers={"X-CSRF-Token": token}
    )
    assert response.status_code == 403
    assert "Not authorized" in response.text
    assert response.text.count("<nav") == 1
