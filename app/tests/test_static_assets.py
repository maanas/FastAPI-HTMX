import os
import re
import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app

pytestmark = pytest.mark.anyio

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
TEMPLATES = APP / "templates"
# The app's own JS and CSS source; vendored and built files are not scanned.
OWN_JS = sorted((APP / "static" / "js").glob("*.js"))
OWN_CSS = sorted((APP / "static" / "css" / "src").glob("*.css"))
CSS_URL = "/static/css/app.css"
INTER_FILES = ("inter-latin-wght-normal.woff2", "inter-latin-ext-wght-normal.woff2")
# A <link> or <script> tag that loads from an absolute http(s) or protocol-relative URL.
EXTERNAL_ASSET = re.compile(
    r"<(?:link|script)\b[^>]*?(?:href|src)\s*=\s*[\"'](?:https?:)?//", re.I | re.S
)
# A JS string literal or a CSS url() or @import that names another origin.
EXTERNAL_JS = re.compile(r"[\"'`](?:https?:)?//[\w.-]+", re.I)
EXTERNAL_CSS = re.compile(r"(?:url\(\s*|@import\s+)[\"']?(?:https?:)?//", re.I)


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


@pytest.mark.parametrize("name", INTER_FILES)
async def test_vendored_inter_font_is_served(client, name):
    response = await client.get(f"/static/vendor/inter/{name}")
    assert response.status_code == 200
    assert response.content


async def test_built_stylesheet_points_at_the_vendored_inter_font(client):
    response = await client.get(CSS_URL)
    for name in INTER_FILES:
        assert f"/static/vendor/inter/{name}" in response.text


def test_templates_load_no_old_or_external_assets():
    templates = list(TEMPLATES.rglob("*.html"))
    assert templates
    for path in templates:
        text = path.read_text(encoding="utf-8")
        assert "flowbite-1.8.1" not in text, path
        assert not EXTERNAL_ASSET.search(text), path


def test_own_js_and_css_load_nothing_from_another_origin():
    assert OWN_JS and OWN_CSS
    for path in OWN_JS:
        assert not EXTERNAL_JS.search(path.read_text(encoding="utf-8")), path
    for path in OWN_CSS:
        assert not EXTERNAL_CSS.search(path.read_text(encoding="utf-8")), path


def test_external_asset_patterns_catch_both_url_forms():
    assert EXTERNAL_ASSET.search('<script src="//cdn.test/a.js"></script>')
    assert EXTERNAL_ASSET.search("<link rel=stylesheet href='https://cdn.test/a.css'>")
    assert not EXTERNAL_ASSET.search('<script src="/static/js/a.js"></script>')
    assert EXTERNAL_JS.search('fetch("//cdn.test/x")')
    assert EXTERNAL_JS.search("import('https://cdn.test/x.js')")
    assert not EXTERNAL_JS.search('fetch("/auth/jwt/login") // comment')
    assert EXTERNAL_CSS.search('@import url("//cdn.test/a.css");')
    assert EXTERNAL_CSS.search("src: url(//cdn.test/a.woff2);")
    assert not EXTERNAL_CSS.search("src: url(/static/vendor/inter/a.woff2);")


def test_built_stylesheet_equals_a_fresh_build(tmp_path):
    """app.css must be what tools/css.sh builds now. Skipped without the Tailwind
    binary (a test never downloads it) or the Flowbite plugin."""
    script = ROOT / "tools" / "css.sh"
    version = re.search(r'^VERSION="([^"]+)"', script.read_text(), re.M).group(1)
    binaries = list((ROOT / "build" / "tailwind").glob(f"tailwindcss-*-{version}"))
    if not any(os.access(b, os.X_OK) for b in binaries):
        pytest.skip("Tailwind binary not downloaded; run tools/css.sh once")
    if not (ROOT / "theme" / "flowbite" / "plugin.js").exists():
        pytest.skip("theme/flowbite submodule not checked out")
    fresh = tmp_path / "app.css"
    subprocess.run(
        [str(script)],
        env={**os.environ, "CSS_OUT": str(fresh)},
        check=True,
        capture_output=True,
    )
    built = (APP / "static" / "css" / "app.css").read_bytes()
    assert fresh.read_bytes() == built, "app.css is stale: run tools/css.sh"
