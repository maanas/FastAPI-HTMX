"""The answer to an HTTPException: its own status and detail, the not-found page for
a browser, the fragment for htmx, and the 401 redirect that suits each caller."""

import re
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from loguru import logger

from app.app import app
from app.core.security_headers import SECURITY_HEADERS
from app.routes.view.errors import ERROR_RENDERED_HEADER

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
HX_CONTENT = {**HX, "HX-Target": "dashboard-body"}
BROWSER = {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
JSON = {"Accept": "application/json"}
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
NOT_FOUND_TITLE = "Page not found | FastAPI HTMX"
DETAIL = "sentinel-detail-7f3a"


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@contextmanager
def raising_route(status, detail=DETAIL):
    """A temporary GET route that raises an HTTPException with `status`."""

    async def raise_it():
        raise HTTPException(status_code=status, detail=detail)

    path = f"/pytest-raises-{status}"
    app.router.add_api_route(path, raise_it)
    route = app.router.routes[-1]
    try:
        yield path
    finally:
        app.router.routes.remove(route)


def vary(response):
    return {v.strip().lower() for v in response.headers["vary"].split(",")}


def assert_headers(response):
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value, name


# --- an unknown path


async def test_a_browser_gets_the_not_found_page(client):
    response = await client.get("/no-such-page", headers=BROWSER)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert TITLE.findall(response.text) == [NOT_FOUND_TITLE]
    assert "<html" in response.text
    # Whether the visitor is signed in is not checked: no navigation for anyone
    assert "<nav" not in response.text
    assert "<aside" not in response.text
    assert "sm:ml-64" not in response.text
    assert 'href="/dashboard"' in response.text
    assert ERROR_RENDERED_HEADER not in response.headers
    assert vary(response) == {"accept", "hx-request", "hx-target"}
    assert_headers(response)


async def test_htmx_gets_the_fragment_marked_as_rendered(client):
    response = await client.get("/no-such-page", headers=HX_CONTENT)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers[ERROR_RENDERED_HEADER] == "1"
    assert TITLE.findall(response.text) == [NOT_FOUND_TITLE]
    assert response.text.startswith("<title>")
    assert "<html" not in response.text
    assert response.text.count('id="dashboard-body"') == 1
    assert "sm:ml-64" in response.text
    assert 'href="/dashboard"' in response.text
    assert vary(response) == {"accept", "hx-request", "hx-target"}
    assert_headers(response)


@pytest.mark.parametrize(
    "target", [{"HX-Target": "upload-result"}, {"HX-Target": "other"}, {}],
    ids=["upload-result", "other-id", "no-target"],
)
async def test_htmx_to_another_target_gets_the_json_404_and_no_marker(client, target):
    response = await client.get("/no-such-page", headers={**HX, **target})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}
    assert ERROR_RENDERED_HEADER not in response.headers
    assert vary(response) == {"accept", "hx-request", "hx-target"}
    assert_headers(response)


async def test_a_history_restore_request_gets_the_page(client):
    headers = {**HX_CONTENT, "HX-History-Restore-Request": "true", **BROWSER}
    response = await client.get("/no-such-page", headers=headers)
    assert response.status_code == 404
    assert "<html" in response.text
    assert ERROR_RENDERED_HEADER not in response.headers


@pytest.mark.parametrize("headers", [JSON, {}], ids=["json", "any"])
@pytest.mark.parametrize("path", ["/no-such-page", "/users/a/b/c", "/auth/nope"])
async def test_a_caller_that_does_not_ask_for_html_gets_json(client, path, headers):
    response = await client.get(path, headers=headers)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}
    assert ERROR_RENDERED_HEADER not in response.headers
    assert_headers(response)


async def test_a_wrong_method_keeps_405_and_allow(client):
    response = await client.post("/dashboard")
    assert response.status_code in (403, 405)
    if response.status_code == 405:
        assert response.json() == {"detail": "Method Not Allowed"}
        assert "GET" in response.headers["allow"]


# --- the status and detail of any other exception


@pytest.mark.parametrize("status", [400, 403, 404, 409, 500])
async def test_status_and_detail_are_kept_as_json(client, status):
    with raising_route(status) as path:
        response = await client.get(path, headers=JSON)
    assert response.status_code == status
    assert response.json() == {"detail": DETAIL}
    assert_headers(response)


async def test_a_403_is_json_even_for_a_browser(client):
    with raising_route(403) as path:
        response = await client.get(path, headers=BROWSER)
    assert response.status_code == 403
    assert response.json() == {"detail": DETAIL}


async def test_a_404_raised_by_a_route_is_the_page_for_a_browser(client):
    with raising_route(404) as path:
        response = await client.get(path, headers=BROWSER)
    assert response.status_code == 404
    assert TITLE.findall(response.text) == [NOT_FOUND_TITLE]
    assert DETAIL not in response.text
    assert vary(response) == {"accept", "hx-request", "hx-target"}


# --- 401


async def test_a_401_redirects_a_browser_to_login(client):
    with raising_route(401) as path:
        response = await client.get(path, headers=BROWSER, follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/login"
    assert vary(response) == {"accept", "hx-request"}
    assert_headers(response)


async def test_a_401_sends_htmx_an_hx_redirect(client):
    with raising_route(401) as path:
        response = await client.get(path, headers=HX, follow_redirects=False)
    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/login"
    assert "location" not in response.headers
    assert response.text == ""
    assert vary(response) == {"accept", "hx-request"}
    assert_headers(response)


async def test_a_401_is_json_for_a_caller_that_asks_for_json_only(client):
    with raising_route(401) as path:
        response = await client.get(path, headers=JSON, follow_redirects=False)
    assert response.status_code == 401
    assert response.json() == {"detail": DETAIL}
    assert "HX-Redirect" not in response.headers
    assert vary(response) == {"accept", "hx-request"}


async def test_a_signed_out_htmx_request_to_a_real_route_gets_hx_redirect(client):
    response = await client.get("/role", headers=HX, follow_redirects=False)
    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/login"
    page = await client.get("/role", headers=BROWSER, follow_redirects=False)
    assert page.headers["location"] == "/login"


async def test_the_log_line_has_method_path_and_status_only(client):
    lines = []
    sink = logger.add(lines.append, level="WARNING")
    try:
        for status in (401, 403):
            with raising_route(status) as path:
                await client.get(path, headers=JSON)
    finally:
        logger.remove(sink)
    log = "".join(lines)
    assert "HTTP 401: GET /pytest-raises-401" in log
    assert "HTTP 403: GET /pytest-raises-403" in log
    assert DETAIL not in log


async def test_the_users_api_answers_a_signed_out_json_caller_with_401_json(client):
    response = await client.get("/users/me", headers=JSON, follow_redirects=False)
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
