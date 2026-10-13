import re
from html.parser import HTMLParser

IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*")
# Parts of an Alpine expression the CSP build cannot parse or that reach for globals
CSP_FORBIDDEN = (
    (re.compile(r"=>"), "an arrow function"),
    (re.compile(r"`"), "a template literal"),
    (re.compile(r"\b(?:window|document)\b"), "a global"),
    (re.compile(r";\s*\S"), "a second statement"),
    (re.compile(r"\{\{"), "Jinja"),
)
RAW_PATTERNS = (CSP_FORBIDDEN[1][0], CSP_FORBIDDEN[4][0])
OPENERS = {"(": ")", "{": "}", "[": "]"}


def _is_alpine_expression(name):
    """x-*, @*, :* attributes hold expressions, except x-transition:* (class lists)."""
    if name.startswith("x-transition"):
        return False
    return name.startswith(("x-", "@", ":"))


def _without_strings(value):
    """The expression with the text inside '...' and "..." literals blanked out."""
    out = []
    quote = ""
    for char in value:
        if quote:
            if char == quote:
                quote = ""
                out.append(char)
        elif char in "'\"":
            quote = char
            out.append(char)
        else:
            out.append(char)
    return "".join(out)


def _has_top_level_comma(code):
    """True for a comma outside (), {} and [] (comma operator), strings removed."""
    depth = 0
    for char in code:
        if char in OPENERS:
            depth += 1
        elif char in OPENERS.values():
            depth -= 1
        elif char == "," and depth == 0:
            return True
    return False


def alpine_csp_problems(name, value):
    """What stops one Alpine attribute from parsing in the @alpinejs/csp build."""
    if name == "x-data":
        if not IDENTIFIER.fullmatch(value.strip()):
            return [f"x-data must be a registered component name, not {value!r}"]
        return []
    if not _is_alpine_expression(name):
        return []
    if name == "x-html":
        return ["x-html is not allowed in the CSP build"]
    # Backtick and Jinja are flagged anywhere; the rest only outside string literals
    code = _without_strings(value)
    problems = [
        f"{name} has {label}"
        for pattern, label in CSP_FORBIDDEN
        if pattern.search(value if pattern in RAW_PATTERNS else code)
    ]
    if _has_top_level_comma(code):
        problems.append(f"{name} has a comma operator")
    return problems


class _RuleScanner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.problems = []

    def handle_starttag(self, tag, attrs):
        names = [name.lower() for name, _ in attrs]
        line = self.getpos()[0]
        if tag == "script" and "src" not in names:
            self.problems.append(f"line {line}: <script> without src")
        for name in names:
            if name == "style":
                self.problems.append(f"line {line}: <{tag}> has a style attribute")
            elif name.startswith("on"):
                self.problems.append(f"line {line}: <{tag}> has handler {name}")
            elif name.startswith("hx-on"):
                self.problems.append(f"line {line}: <{tag}> has htmx handler {name}")
        for name, value in attrs:
            for problem in alpine_csp_problems(name.lower(), value or ""):
                self.problems.append(f"line {line}: <{tag}> {problem}")

    handle_startendtag = handle_starttag


def template_rule_violations(text):
    """Inline scripts, style attributes, on* and hx-on handlers and Alpine attributes
    the CSP build cannot parse, found in a template."""
    scanner = _RuleScanner()
    scanner.feed(text)
    scanner.close()
    return scanner.problems
