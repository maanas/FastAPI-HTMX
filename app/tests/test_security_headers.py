import json
import re

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.app import app
from app.core.security_headers import (
    CONTENT_SECURITY_POLICY,
    SECURITY_HEADERS,
    SecurityHeadersMiddleware,
)

pytestmark = pytest.mark.anyio

HSTS = "Strict-Transport-Security"


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def assert_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value, name


def parse_csp(value):
    directives = {}
    for part in value.split(";"):
        name, *sources = part.split()
        directives[name] = sources
    return directives


def test_the_expected_header_values():
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
    assert SECURITY_HEADERS["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert SECURITY_HEADERS["Cross-Origin-Opener-Policy"] == "same-origin"
    for feature in ("camera", "microphone", "geolocation"):
        assert f"{feature}=()" in SECURITY_HEADERS["Permissions-Policy"]


def test_the_policy_is_own_origin_only():
    csp = parse_csp(CONTENT_SECURITY_POLICY)
    assert csp["script-src"] == ["'self'"]
    assert csp["default-src"] == ["'self'"]
    assert csp["object-src"] == ["'none'"]
    assert csp["frame-ancestors"] == ["'none'"]
    sources = [s for values in csp.values() for s in values]
    assert "'unsafe-inline'" not in sources
    assert "'unsafe-eval'" not in sources
    assert "*" not in sources
    assert not [s for s in sources if re.match(r"(?:https?:|//)", s)]


async def test_a_page_has_the_headers(client):
    response = await client.get("/login")
    assert response.status_code == 200
    assert_security_headers(response)
    assert HSTS not in response.headers


async def test_a_static_file_has_the_headers(client):
    response = await client.get("/static/css/app.css")
    assert response.status_code == 200
    assert_security_headers(response)


async def test_a_redirect_has_the_headers(client):
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert_security_headers(response)


async def test_the_csrf_403_has_the_headers(client):
    response = await client.post("/auth/jwt/login", data={})
    assert response.status_code == 403
    assert_security_headers(response)


async def test_a_404_has_the_headers(client):
    response = await client.get("/no-such-page")
    assert response.status_code == 404
    assert_security_headers(response)


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_the_api_docs_are_off(client, path):
    assert (await client.get(path)).status_code == 404


async def _get(hsts, headers=None):
    async def page(request):
        return PlainTextResponse("ok", headers=headers)

    inner = Starlette(routes=[Route("/", page)])
    wrapped = SecurityHeadersMiddleware(inner, hsts=hsts)
    async with AsyncClient(
        transport=ASGITransport(app=wrapped), base_url="http://test"
    ) as c:
        return await c.get("/")


@pytest.mark.parametrize("hsts", [False, True])
async def test_hsts_follows_cookie_secure(hsts):
    response = await _get(hsts)
    if hsts:
        assert response.headers[HSTS] == "max-age=31536000; includeSubDomains"
    else:
        assert HSTS not in response.headers


async def test_a_header_the_route_set_is_kept():
    response = await _get(False, {"X-Frame-Options": "SAMEORIGIN"})
    assert response.headers.get_list("X-Frame-Options") == ["SAMEORIGIN"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def htmx_config(html):
    meta = re.search(r"<meta name=\"htmx-config\" content='([^']*)'", html)
    assert meta, "no htmx-config meta"
    return json.loads(meta.group(1)), meta.start()


@pytest.mark.parametrize("path", ["/login", "/register"])
async def test_the_base_templates_configure_htmx(client, path):
    html = (await client.get(path)).text
    config, position = htmx_config(html)
    assert config["allowEval"] is False
    assert config["allowScriptTags"] is False
    assert config["includeIndicatorStyles"] is False
    assert config["selfRequestsOnly"] is True
    assert position < html.index("htmx.min.js")
