import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app
from app.tests.template_rules import template_rule_violations

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_login_page_has_form_fields_and_csrf_token(client):
    response = await client.get("/login")
    assert response.status_code == 200
    assert 'x-data="login"' in response.text
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text
    token = re.search(r'data-csrf-token="([^"]+)"', response.text)
    assert token
    assert "csrf" in response.headers["set-cookie"].lower()
    assert "<nav" not in response.text


async def test_register_page_has_form_fields(client):
    response = await client.get("/register")
    assert response.status_code == 200
    assert 'x-data="register"' in response.text
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text
    assert 'id="repeatPassword"' in response.text
    assert "<nav" not in response.text


def test_rule_scanner_sees_attributes_after_an_arrow_in_a_value():
    tag = '<div data-note="() => {{}}" {} class="a">'
    assert template_rule_violations(tag.format('onclick="x()"'))
    assert template_rule_violations(tag.format('style="color: red"'))
    assert template_rule_violations("<script>x()</script>")
    assert not template_rule_violations(
        '<div data-note="() => {}" @click="go()" x-on:input="go()" '
        'hx-get="{{ url_for(\'a\') }}"><script src="/a.js"></script></div>'
    )
