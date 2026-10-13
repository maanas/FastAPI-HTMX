from html.parser import HTMLParser


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

    handle_startendtag = handle_starttag


def template_rule_violations(text):
    """Inline scripts, style attributes, on* and hx-on handlers found in a template."""
    scanner = _RuleScanner()
    scanner.feed(text)
    scanner.close()
    return scanner.problems
