from typing import Dict

from fastapi import Request

from app.templates import templates


def wants_fragment(request: Request) -> bool:
    """True for an HTMX request that swaps content in place.

    A history restore request carries HX-Request too but swaps the whole body,
    so it needs the full page.
    """
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


def render_view(request: Request, page: str, fragment: str, context: Dict, **kwargs):
    """Render the fragment for an HTMX request and the full page for any other.

    `page` extends the layout and only includes `fragment`; the fragment has no
    layout and its root carries the id the sidebar link targets.
    """
    response = templates.TemplateResponse(
        request, fragment if wants_fragment(request) else page, context, **kwargs
    )
    response.headers["Vary"] = "HX-Request"
    return response
