import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app

pytestmark = pytest.mark.anyio

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
CSS_URL = "/static/css/app.css"
# A <link> or <script> tag that loads from an absolute http(s) URL.
EXTERNAL_ASSET = re.compile(
    r"<(?:link|script)\b[^>]*?(?:href|src)\s*=\s*[\"']https?://", re.I | re.S
)


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_built_stylesheet_is_served_as_css(client):
    response = await client.get(CSS_URL)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


async def test_login_page_links_the_built_stylesheet(client):
    response = await client.get("/login")
    assert response.status_code == 200
    assert f'href="{CSS_URL}"' in response.text


def test_templates_load_no_old_or_external_assets():
    templates = list(TEMPLATES.rglob("*.html"))
    assert templates
    for path in templates:
        text = path.read_text(encoding="utf-8")
        assert "flowbite-1.8.1" not in text, path
        assert not EXTERNAL_ASSET.search(text), path
