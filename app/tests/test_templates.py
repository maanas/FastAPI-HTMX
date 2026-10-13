"""Repo-wide template rules. Every file under app/templates/ is found by walking the
directory, so a new template is covered without touching this file."""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app.tests.template_rules import template_rule_violations

APP = Path(__file__).resolve().parents[1]
TEMPLATES = APP / "templates"
BUILT_CSS = APP / "static" / "css" / "app.css"
ALL_TEMPLATES = sorted(TEMPLATES.rglob("*.html"))

# Classes that are JS or test hooks and have no CSS rule on purpose, one comment each.
CLASS_ALLOWLIST: dict[str, str] = {}

URL_ATTRS = ("action", "hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete")
EXTERNAL = re.compile(r"^\s*(?:https?:)?//", re.I)
JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"")
CSS_SELECTOR_CLASS = re.compile(r"(?<![\d\w])\.((?:\\.|[\w-])+)")
CSS_HEX_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6})\s?")
CSS_CHAR_ESCAPE = re.compile(r"\\(.)")


class _Scanner(HTMLParser):
    """Collects what the template tests look at, one tag at a time."""

    def __init__(self):
        super().__init__()
        self.loads = []  # (kind, url) for script src and stylesheet href
        self.urls = []  # (attr, url) for every attribute that fetches a page or file
        self.classes = set()

    def handle_starttag(self, tag, attrs):
        attrs = {name: value or "" for name, value in attrs}
        if tag == "script" and "src" in attrs:
            self.loads.append(("script src", attrs["src"]))
        if tag == "link" and "href" in attrs:
            self.urls.append(("link href", attrs["href"]))
            if "stylesheet" in attrs.get("rel", "").lower():
                self.loads.append(("stylesheet href", attrs["href"]))
        for name in URL_ATTRS:
            if name in attrs:
                self.urls.append((name, attrs[name]))
        if "srcset" in attrs:
            for candidate in attrs["srcset"].split(","):
                self.urls.append(("srcset", candidate.strip().split(" ")[0]))
        if "src" in attrs and tag != "script":
            self.urls.append(("src", attrs["src"]))
        if "class" in attrs:
            self.classes.update(JINJA.sub(" ", attrs["class"]).split())
        for name in (":class", "x-bind:class"):
            if name in attrs:
                for single, double in QUOTED.findall(JINJA.sub(" ", attrs[name])):
                    self.classes.update((single or double).split())

    handle_startendtag = handle_starttag


def scan(text):
    scanner = _Scanner()
    scanner.feed(text)
    scanner.close()
    return scanner


def built_css_classes(css):
    """Class names that appear as selectors in the built CSS, with escapes undone."""
    names = set()
    for raw in CSS_SELECTOR_CLASS.findall(css):
        name = CSS_HEX_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), raw)
        names.add(CSS_CHAR_ESCAPE.sub(r"\1", name))
    return names


def unknown_classes(text, known):
    return sorted(scan(text).classes - known - CLASS_ALLOWLIST.keys())


@pytest.fixture(scope="module")
def css_classes():
    return built_css_classes(BUILT_CSS.read_text(encoding="utf-8"))


def ids(path):
    return str(path.relative_to(TEMPLATES))


def test_templates_are_found():
    assert len(ALL_TEMPLATES) >= 30


@pytest.mark.parametrize("path", ALL_TEMPLATES, ids=ids)
def test_template_has_no_inline_script_style_or_handler(path):
    assert not template_rule_violations(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", ALL_TEMPLATES, ids=ids)
def test_template_loads_only_from_static_and_fetches_nothing_external(path):
    found = scan(path.read_text(encoding="utf-8"))
    for kind, url in found.loads:
        assert url.startswith("/static/"), (kind, url)
    for kind, url in found.urls:
        assert not EXTERNAL.match(url), (kind, url)


@pytest.mark.parametrize("path", ALL_TEMPLATES, ids=ids)
def test_template_layout_matches_its_folder(path):
    text = path.read_text(encoding="utf-8")
    folder = path.relative_to(TEMPLATES).parts[0]
    if folder == "partials":
        assert "{% extends" not in text
        assert "<html" not in text
    elif folder == "pages":
        assert re.search(r'\{%\s*extends\s+"base/', text)


@pytest.mark.parametrize("path", ALL_TEMPLATES, ids=ids)
def test_template_classes_exist_in_the_built_css(path, css_classes):
    assert not unknown_classes(path.read_text(encoding="utf-8"), css_classes)


def test_class_check_finds_a_made_up_class(css_classes):
    assert "hidden" in css_classes
    assert "hover:bg-brand-strong" in css_classes
    assert "py-2.5" in css_classes or "px-3" in css_classes
    html = '<div class="hidden hover-bg-blue-800 hover:bg-brand-strong"></div>'
    assert unknown_classes(html, css_classes) == ["hover-bg-blue-800"]
    bound = """<div :class="{ 'hidden': a, 'hover-bg-blue-800 block': b }"></div>"""
    assert unknown_classes(bound, css_classes) == ["hover-bg-blue-800"]
    bound = """<div x-bind:class="a ? 'block' : 'hover-bg-blue-800'"></div>"""
    assert unknown_classes(bound, css_classes) == ["hover-bg-blue-800"]


def test_class_allowlist_stays_small():
    assert len(CLASS_ALLOWLIST) <= 3


def test_css_class_reader_undoes_tailwind_escapes():
    css = r".hover\:bg-brand:hover{a:b}.w-1\/2{a:b}.py-2\.5{a:b}.\32xl\:p-4{a:b}"
    assert built_css_classes(css) == {"hover:bg-brand", "w-1/2", "py-2.5", "2xl:p-4"}


def test_url_check_flags_absolute_and_protocol_relative_urls():
    found = scan(
        '<a hx-get="//evil.test/x"></a><form action="https://evil.test"></form>'
        '<img srcset="//cdn.test/a.png 2x"><link rel="stylesheet" href="/a.css">'
    )
    assert [kind for kind, url in found.urls if EXTERNAL.match(url)] == [
        "hx-get",
        "action",
        "srcset",
    ]
    assert found.loads == [("stylesheet href", "/a.css")]
