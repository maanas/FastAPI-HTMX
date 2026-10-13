from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_csrf_protect.exceptions import CsrfProtectError
from loguru import logger


async def http_exception_handler(request: Request, exc: HTTPException):
    if exc and exc.status_code == 401:
        return RedirectResponse("/login")
    # elif request.scope.get("path") == "/auth/jwt/login" and exc.status_code == 400:
    #     return templates.TemplateResponse("pages/login.html", {"request": request, "error": "Incorrect username or password"})
    else:
        route = request.scope.get("path")
        method = request.scope.get("method")
        logger.error(
            f"Error in route {method} {route}: {exc.detail} : {exc.status_code}"
        )
        # if route == "/auth/jwt/login" and exc.status_code == 400:
        return Response(content="Error managed via HTTP module", status_code=400)


async def csrf_error_handler(request: Request, exc: CsrfProtectError):
    # A fixed message: the exception text can name the token or the cookie
    logger.warning(f"CSRF check failed: {request.method} {request.scope.get('path')}")
    return JSONResponse(
        status_code=403, content={"detail": "CSRF token missing or invalid"}
    )
