"""Repo-wide template rules. Every file under app/templates/ is found by walking the
directory, so a new template is covered without touching this file."""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app.tests.template_rules import alpine_csp_problems, template_rule_violations

APP = Path(__file__).resolve().parents[1]
TEMPLATES = APP / "templates"
BUILT_CSS = APP / "static" / "css" / "app.css"
OWN_JS = sorted((APP / "static" / "js").glob("*.js"))
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
HYPERSCRIPT = re.compile(r"hyperscript", re.I)
# Hyperscript's attributes: _="...", script="..." and data-script="..."
HYPERSCRIPT_ATTRS = ("_", "script", "data-script")


class _Scanner(HTMLParser):
    """Collects what the template tests look at, one tag at a time."""

    def __init__(self):
        super().__init__()
        self.loads = []  # (kind, url) for script src and stylesheet href
        self.urls = []  # (attr, url) for every attribute that fetches a page or file
        self.classes = set()
        self.attr_names = set()

    def handle_starttag(self, tag, attrs):
        attrs = {name: value or "" for name, value in attrs}
        if tag == "script" and "src" in attrs:
            self.loads.append(("script src", attrs["src"]))
        if tag == "link" and "href" in attrs:
            self.urls.append(("link href", attrs["href"]))
            if "stylesheet" in attrs.get("rel", "").lower():
                self.loads.append(("stylesheet href", attrs["href"]))
        self.attr_names.update(attrs)
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


@pytest.mark.parametrize("path", ALL_TEMPLATES, ids=ids)
def test_template_has_no_hyperscript(path):
    text = path.read_text(encoding="utf-8")
    assert not HYPERSCRIPT.search(text)
    assert not scan(text).attr_names & set(HYPERSCRIPT_ATTRS)


def test_hyperscript_is_gone_from_static_files():
    assert not (APP / "static" / "vendor" / "hyperscript").exists()
    assert OWN_JS
    for path in OWN_JS:
        assert not HYPERSCRIPT.search(path.read_text(encoding="utf-8")), path


def test_user_edit_cancel_is_an_htmx_button_with_a_confirm():
    text = (TEMPLATES / "partials/user/edit_user.html").read_text(encoding="utf-8")
    cancel = re.search(r"<button\s[^>]*>\s*Cancel\s*</button>", text, re.S).group(0)
    assert "hx-get=" in cancel
    assert "hx-confirm=" in cancel
    assert "@click" not in cancel and "x-on:click" not in cancel
    assert "cancelEdit" not in text and "data-list-url" not in text


@pytest.mark.parametrize(
    "attr", ['@click="reset"', '@click.prevent="cancel"', 'x-on:click="cancel"']
)
def test_confirm_guard_flags_an_alpine_click_next_to_hx_confirm(attr):
    html = f'<button hx-get="/a" hx-confirm="Sure?" {attr}>Cancel</button>'
    assert any("hx-confirm" in p for p in template_rule_violations(html))


def test_confirm_guard_accepts_the_words_in_strings_and_separate_elements():
    assert not template_rule_violations(
        '<button hx-get="/a" hx-confirm="Click @click to leave?">Cancel</button>'
        '<button x-data="c" @click="go">Go</button>'
    )


def test_hyperscript_check_finds_its_attributes():
    found = scan('<input _="on click" data-script="x"><p script="y"></p>')
    assert found.attr_names & set(HYPERSCRIPT_ATTRS) == set(HYPERSCRIPT_ATTRS)


@pytest.mark.parametrize(
    "html",
    [
        "<div x-data></div>",
        '<div x-data=""></div>',
        '<div x-data="{ open: false }"></div>',
        '<div x-data="a.b"></div>',
    ],
)
def test_csp_check_needs_a_component_name_in_x_data(html):
    assert any("x-data" in p for p in template_rule_violations(html))
    assert not template_rule_violations('<div x-data="login"></div>')


@pytest.mark.parametrize(
    "attr",
    [
        "x-init=\"$watch('a', v => b())\"",
        'x-text="`hi ${name}`"',
        '@click="window.location.href = u"',
        ':class="document.title"',
        'x-on:change="a = 1; b = 2"',
        '@input="a(), b()"',
        '@input="a({{ token }})"',
        'x-show="a, b"',
        'x-html="content"',
    ],
)
def test_csp_check_flags_expressions_the_parser_rejects(attr):
    assert template_rule_violations(f'<div x-data="c" {attr}></div>')


@pytest.mark.parametrize(
    "attr",
    [
        'x-show="open"',
        '@click="f(a, b)"',
        '@click="go;"',
        ":class=\"{ 'hidden': !a, 'block b': c }\"",
        ":class=\"a ? 'x, y' : 'z'\"",
        'x-bind:disabled="!a || b"',
        'x-transition:leave="transition ease-in duration-1000"',
        'x-on:htmx:validation:validate="validate"',
        'x-model="name"',
        ":class=\"a ? 'document; x' : 'window'\"",
        "x-cloak",
    ],
)
def test_csp_check_accepts_single_expressions(attr):
    assert not template_rule_violations(f'<div x-data="c" {attr}></div>')


def test_csp_check_ignores_non_alpine_attributes():
    assert alpine_csp_problems("data-x", "a => b") == []


EVAL_FEATURES = (
    '<div hx-on:click="go()"></div>',
    '<div hx-on::after-request="go()"></div>',
    "<div hx-vals='js:{a: 1}'></div>",
    "<div hx-vals='javascript:{a: 1}'></div>",
    "<div hx-headers='js:{a: 1}'></div>",
    "<input hx-trigger=\"keyup[key=='Enter']\">",
)
EVAL_FREE = (
    '<div hx-trigger="revealed" hx-vals=\'{"a": "js:x"}\'></div>',
    '<div hx-headers=\'{"X-CSRF-Token": "{{ t }}"}\' hx-trigger="keyup changed"></div>',
    '<p title="hx-on and js: are only words here">hx-vals js:</p>',
)


@pytest.mark.parametrize("html", EVAL_FEATURES)
def test_eval_guard_flags_each_feature_allow_eval_false_disables(html):
    assert template_rule_violations(html)


@pytest.mark.parametrize("html", EVAL_FREE)
def test_eval_guard_leaves_eval_free_markup_alone(html):
    assert not template_rule_violations(html)
