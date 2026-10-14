from fastapi import Request, Response
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_csrf_protect.exceptions import CsrfProtectError
from loguru import logger
from starlette.exceptions import HTTPException

from app.routes.view.errors import ERROR_RENDERED_HEADER
from app.routes.view.fragments import (
    CONTENT_TARGET_ID,
    accepts_html,
    add_vary,
    render_view,
    wants_fragment,
)

NOT_FOUND_PAGE = "pages/not_found.html"
NOT_FOUND_FRAGMENT = "partials/errors/not_found.html"
# What the answer depends on, for caches
VARY_401 = ("Accept", "HX-Request")
VARY_404 = ("Accept", "HX-Request", "HX-Target")


async def http_exception_handler(request: Request, exc: HTTPException):
    """Answer an HTTPException with its own status and detail.

    Registered for Starlette's HTTPException, so FastAPI's (a subclass) and the
    router's own 404 for an unknown path are covered. JSON `{"detail": ...}` as
    FastAPI answers by default, except:
    - 401: an HTMX request gets `HX-Redirect: /login` (a 3xx would be followed by
      the XHR and the login page swapped into the target), a request that asks for
      JSON only gets the 401, any other a redirect to `/login`;
    - 404 for a request that accepts HTML: the not-found page; for an HTMX request
      that targets the content area (`HX-Target: dashboard-body`), its fragment,
      marked as rendered so htmx swaps it. Another target gets the JSON 404.
    The log line has method, path and status only: a 401 detail or header may
    hold a token.
    """
    logger.warning(
        f"HTTP {exc.status_code}: {request.method} {request.scope.get('path')}"
    )
    if exc.status_code == 401:
        if wants_fragment(request):
            response = Response(status_code=401, headers={"HX-Redirect": "/login"})
            add_vary(response, *VARY_401)
            return response
        accept = request.headers.get("Accept", "")
        if accepts_html(request) or "application/json" not in accept:
            response = RedirectResponse("/login")
            add_vary(response, *VARY_401)
            return response
        response = await default_http_exception_handler(request, exc)
        add_vary(response, *VARY_401)
        return response
    if exc.status_code == 404:
        in_shell = wants_fragment(request)
        # An HTMX request gets the card only when it targets the content area: in
        # another target (a table, a popover, the login card) it would break the
        # layout, so those get the JSON 404 without the marker and swap nothing
        if in_shell:
            render = request.headers.get("HX-Target") == CONTENT_TARGET_ID
        else:
            render = accepts_html(request)
        if render:
            response = render_view(
                request,
                NOT_FOUND_PAGE,
                NOT_FOUND_FRAGMENT,
                {"request": request, "in_shell": in_shell},
                status_code=404,
            )
            if in_shell:
                response.headers[ERROR_RENDERED_HEADER] = "1"
        else:
            response = await default_http_exception_handler(request, exc)
        add_vary(response, *VARY_404)
        return response
    return await default_http_exception_handler(request, exc)


async def csrf_error_handler(request: Request, exc: CsrfProtectError):
    # A fixed message: the exception text can name the token or the cookie
    logger.warning(f"CSRF check failed: {request.method} {request.scope.get('path')}")
    return JSONResponse(
        status_code=403, content={"detail": "CSRF token missing or invalid"}
    )
