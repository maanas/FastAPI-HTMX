import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app
from app.database.security import current_active_user

pytestmark = pytest.mark.anyio

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
SHELL_DIRS = (TEMPLATES / "base", TEMPLATES / "partials" / "shell")
SCRIPT_WITHOUT_SRC = re.compile(r"<script\b(?![^>]*\bsrc\s*=)", re.I)
INLINE_STYLE = re.compile(r"<[^>]*\sstyle\s*=", re.I)
INLINE_HANDLER = re.compile(r"<[^>]*\son[a-z]+\s*=", re.I)
ADMIN_LINKS = ("/role", "/user", "/groups", "/uploads")


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def logged_in():
    user = SimpleNamespace(email="admin@example.com", is_superuser=True)
    app.dependency_overrides[current_active_user] = lambda: user
    yield user
    app.dependency_overrides.pop(current_active_user, None)


async def test_dashboard_renders_navbar_and_sidebar(client, logged_in):
    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert "<nav" in response.text
    assert 'id="top-bar-sidebar"' in response.text
    assert 'id="dashboard-body"' in response.text
    assert "admin@example.com" in response.text


async def test_sidebar_shows_admin_links_to_a_superuser(client, logged_in):
    sidebar = (await client.get("/dashboard")).text.split('id="top-bar-sidebar"')[1]
    for link in ADMIN_LINKS:
        assert f'href="http://test{link}"' in sidebar or f'href="{link}"' in sidebar


async def test_sidebar_hides_admin_links_from_a_regular_user(client, logged_in):
    logged_in.is_superuser = False
    response = await client.get("/dashboard")
    assert "data-logout" in response.text
    sidebar = response.text.split('id="top-bar-sidebar"')[1]
    for link in ADMIN_LINKS:
        assert f'{link}"' not in sidebar


async def test_login_page_has_no_navbar_or_sidebar(client):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "<nav" not in response.text
    assert 'id="top-bar-sidebar"' not in response.text


def test_shell_templates_have_no_inline_script_style_or_handler():
    files = [p for d in SHELL_DIRS for p in d.rglob("*.html")]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert not SCRIPT_WITHOUT_SRC.search(text), path
        assert not INLINE_STYLE.search(text), path
        assert not INLINE_HANDLER.search(text), path
