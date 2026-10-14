from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi_csrf_protect.exceptions import CsrfProtectError
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.exceptions import HTTPException

from app.database.db import User
from app.database.security import (
    auth_backend,
    current_active_user,
    fastapi_users,
    refuse_self_delete,
    require_csrf,
)
from app.exception import csrf_error_handler, http_exception_handler
from app.routes.view.group import group_view_route

# importing the route
from app.routes.view.login import login_view_route
from app.routes.view.role import role_view_route
from app.routes.view.upload import upload_view_route
from app.routes.view.user import user_view_route
from app.schema.users import UserCreate, UserRead, UserUpdate

from fastapi_csrf_protect import CsrfProtect

from app.core.csrf_settings import CsrfSettings, crsf_settings
from app.core.security_headers import SecurityHeadersMiddleware

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Application started")
    yield
    logger.info("Application shutdown")


# The API docs pages load Swagger UI from a CDN with an inline script: both are
# refused by the content security policy and the no-CDN rule, so they are off
app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    exception_handlers={
        # Starlette's class: FastAPI's HTTPException and the router's 404 are covered
        HTTPException: http_exception_handler,
        CsrfProtectError: csrf_error_handler,
    }
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
# HSTS only when the site is served over HTTPS (COOKIE_SECURE)
app.add_middleware(SecurityHeadersMiddleware, hsts=crsf_settings.cookie_secure)


# Every POST of the fastapi-users routers needs the CSRF pair (login included,
# logout exempt, see require_csrf), checked before the body is read
csrf_guard = [Depends(require_csrf)]

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
    dependencies=csrf_guard,
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
    dependencies=csrf_guard,
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
    dependencies=csrf_guard,
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
    dependencies=csrf_guard,
)
# PATCH and DELETE need the pair too; a superuser cannot delete themselves here
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_csrf), Depends(refuse_self_delete)],
)


app.include_router(login_view_route, tags=["Pages", "Authentication/Create"])
app.include_router(role_view_route, tags=["Pages", "Role"])
app.include_router(group_view_route, tags=["Pages", "Group"])
app.include_router(user_view_route, tags=["Pages", "User"])
app.include_router(upload_view_route, tags=["Pages", "Upload"])


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    logger.info(user.id)
    return {"message": f"Hello {user.email}!"}


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()
