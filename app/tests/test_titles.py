"""One title per view: the full page and the HTMX answer carry the same one."""

import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.app import app
from app.database.security import current_active_user

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
SUFFIX = " | FastAPI HTMX"
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
UNKNOWN = uuid.uuid4()
TITLE = re.compile(r"<title>(.*?)</title>", re.S)

# (url, the view's name). The ids are unknown: the answer is the view's own error
# page, which keeps the title of the view it renders (see handle_error).
VIEWS = [
    ("/role", "Roles"),
    ("/get_create_roles", "Add role"),
    (f"/get_role/{UNKNOWN}", "Edit role"),
    ("/groups", "Groups"),
    ("/get_create_group", "Add group"),
    (f"/get_group/{UNKNOWN}", "Edit group"),
    (f"/get_group_users/{UNKNOWN}", "Group users"),
    ("/user", "Users"),
    ("/get_create_users", "Add user"),
    (f"/get_user/{UNKNOWN}", "Edit user"),
    ("/uploads", "Upload"),
]


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


@pytest.mark.parametrize("url, name", VIEWS, ids=[v[0].split("/")[1] for v in VIEWS])
async def test_page_and_fragment_carry_the_same_title(client, logged_in, url, name):
    page = await client.get(url)
    fragment = await client.get(url, headers=HX)
    expected = [name + SUFFIX]
    assert TITLE.findall(page.text) == expected
    assert TITLE.findall(fragment.text) == expected
    assert page.status_code == fragment.status_code
    assert "<html" in page.text
    assert "<html" not in fragment.text
    # The wrapper puts the title first, as htmx reads it at the top of the response
    assert fragment.text.startswith("<title>")
    # The page has it in the head only, never in the body where the fragment is
    assert "<title" not in page.text.split("<body", 1)[1]


async def test_the_dashboard_page_has_its_title(client, logged_in):
    response = await client.get("/dashboard")
    assert TITLE.findall(response.text) == ["Dashboard" + SUFFIX]


def test_a_title_is_escaped_once(monkeypatch):
    from jinja2 import ChoiceLoader, DictLoader

    from app.routes.view.fragments import view_title
    from app.templates import jinja_env

    pages = {
        "pages/pytest_title.html": (
            "{% extends 'base/base.html' %}"
            "{% block title %}{{ name }}{% endblock %}"
        ),
        "partials/pytest_title.html": "<p>body</p>",
    }
    monkeypatch.setattr(
        jinja_env, "loader", ChoiceLoader([DictLoader(pages), jinja_env.loader])
    )
    title = view_title("pages/pytest_title.html", {"name": "<b>x</b> & y"})
    assert title == "<b>x</b> & y"
    wrapper = jinja_env.get_template("base/fragment.html").render(
        fragment_title=title, fragment_template="partials/pytest_title.html"
    )
    assert wrapper.startswith("<title>&lt;b&gt;x&lt;/b&gt; &amp; y</title>")


def test_a_view_without_a_title_block_gets_no_title_element():
    from app.routes.view.fragments import view_title

    assert view_title("partials/role/role_list.html", {}) == ""


async def test_the_files_table_is_not_a_view_and_has_no_title(client, logged_in):
    response = await client.get("/get_uploaded_files", headers=HX)
    assert response.status_code == 200
    assert "<title" not in response.text


def test_no_partial_has_a_title_element():
    for path in sorted((TEMPLATES / "partials").rglob("*.html")):
        assert "<title" not in path.read_text(), path


def page_templates():
    return sorted((TEMPLATES / "pages").glob("*.html"))


TITLE_BLOCK = re.compile(r"\{% block title %\}([^{}]+)\{% endblock %\}")


def title_problems(source):
    """Why a page template does not define its title through the one mechanism:
    one literal `{% block title %}<View> | FastAPI HTMX{% endblock %}`, no element."""
    blocks = TITLE_BLOCK.findall(source)
    if len(blocks) != 1:
        return ["needs exactly one literal title block"]
    problems = []
    if not blocks[0].endswith(SUFFIX) or len(blocks[0]) == len(SUFFIX):
        problems.append("the title must be '<View>" + SUFFIX + "'")
    if "<title" in source:
        problems.append("a page must not write a <title> element")
    return problems


@pytest.mark.parametrize("path", page_templates(), ids=lambda p: p.name)
def test_every_page_defines_its_title_in_one_literal_block(path):
    assert title_problems(path.read_text()) == [], path


@pytest.mark.parametrize(
    "source",
    [
        "{% block title %}{{ title }}{% endblock %}",
        "{% block content %}{% endblock %}",
        "{% block title %}Roles{% endblock %}",
        "{% block title %} | FastAPI HTMX{% endblock %}",
        "{% block title %}A | FastAPI HTMX{% endblock %}<title>A</title>",
        "{% block title %}A | FastAPI HTMX{% endblock %}"
        "{% block title %}B | FastAPI HTMX{% endblock %}",
    ],
)
def test_the_title_guard_flags_a_page_that_breaks_the_rule(source):
    assert title_problems(source)


def test_the_title_guard_accepts_the_word_in_text():
    source = (
        '{% extends "base/auth_base.html" %}\n'
        "{% block title %}Roles | FastAPI HTMX{% endblock %}\n"
        '{% block content %}<p class="title">a title</p>{% endblock %}'
    )
    assert title_problems(source) == []
