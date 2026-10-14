from typing import Dict

from fastapi import Request
from markupsafe import Markup

from app.templates import templates

# The id of the content area every view fragment replaces (outerHTML); htmx sends it
# as the HX-Target header of a request that targets it
CONTENT_TARGET_ID = "dashboard-body"
# Wraps a fragment for an HTMX answer: the view's title, then the fragment
FRAGMENT_WRAPPER = "base/fragment.html"


def wants_fragment(request: Request) -> bool:
    """True for an HTMX request that swaps content in place.

    A history restore request carries HX-Request too but swaps the whole body,
    so it needs the full page.
    """
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


def add_vary(response, *names: str) -> None:
    """Add `names` to the Vary header, keeping the values already there."""
    current = response.headers.get("Vary", "")
    present = [v.strip() for v in current.split(",") if v.strip()]
    lower = {v.lower() for v in present}
    present += [n for n in names if n.lower() not in lower]
    response.headers["Vary"] = ", ".join(present)


def accepts_html(request: Request) -> bool:
    """True when the client asks for HTML (a browser navigation), not JSON."""
    return "text/html" in request.headers.get("Accept", "")


def view_title(page: str, context: Dict) -> str:
    """The text of `page`'s title block, rendered with `context` (autoescaped).

    The title lives in the page template only; this reads it for the fragment
    answer, so both carry the same text. The block output is HTML, so it becomes
    plain text here and the wrapper escapes it once. Empty without a title block.
    """
    template = templates.get_template(page)
    block = template.blocks.get("title")
    if block is None:
        return ""
    html = Markup("".join(block(template.new_context(context))))
    return html.striptags().strip()


def render_view(request: Request, page: str, fragment: str, context: Dict, **kwargs):
    """Render the fragment for an HTMX request and the full page for any other.

    `page` extends the layout, defines the view's title and only includes
    `fragment`; the fragment has no layout and its root carries the id the sidebar
    link targets. The fragment answer is wrapped in `base/fragment.html`, which puts
    the page's title in front: htmx sets `document.title` from a top-level `<title>`
    of a swapped response.
    """
    if wants_fragment(request):
        context = {
            **context,
            "fragment_template": fragment,
            "fragment_title": view_title(page, context),
        }
        name = FRAGMENT_WRAPPER
    else:
        name = page
    response = templates.TemplateResponse(request, name, context, **kwargs)
    add_vary(response, "HX-Request")
    return response
