import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from fastapi_csrf_protect import CsrfProtect
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from loguru import logger

from app.core.auth_settings import get_auth_secret
from app.core.csrf_settings import CsrfSettings, crsf_settings
from app.database.db import User, get_user_db
from app.routes.view.csrf import rotate_csrf_cookie

SECRET: str = get_auth_secret()


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.info(f"User {user.id} requested a password reset.")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.info(f"Verification requested for user {user.id}.")

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ):
        # A new CSRF pair for the new session; the cookie from before login is dropped
        if response is not None:
            rotate_csrf_cookie(response)
        logger.info(f"User {user.id} logged in.")


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


def build_cookie_transport(settings: CsrfSettings) -> CookieTransport:
    """The login cookie: HttpOnly, with Secure and SameSite from the CSRF settings."""
    return CookieTransport(
        cookie_max_age=3600,
        cookie_secure=settings.cookie_secure,
        cookie_httponly=True,
        cookie_samesite=settings.cookie_samesite,
    )


cookie_transport = build_cookie_transport(crsf_settings)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


async def verify_jwt(jwt_token: str, user_manager: UserManager) -> bool:
    """True if the login cookie value is a valid token of an active user.

    The check is the one the auth backend makes: same secret, audience, expiry.
    """
    user = await get_jwt_strategy().read_token(jwt_token, user_manager)
    return user is not None and user.is_active


fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)


# The name fastapi-users gives the logout route of the "jwt" backend
LOGOUT_ROUTE_NAME = "auth:jwt.logout"


async def require_csrf(request: Request, csrf_protect: CsrfProtect = Depends()) -> None:
    """Router dependency: an unsafe request needs a valid CSRF header and cookie pair.

    A failure raises CsrfProtectError, which the app answers with a fixed 403.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    # Log out is exempt: the shell posts it without a token (shell pages carry
    # none), and a forged log out costs the user one login. Login stays checked.
    route = request.scope.get("route")
    if getattr(route, "name", None) == LOGOUT_ROUTE_NAME:
        return
    await csrf_protect.validate_csrf(request)


async def refuse_self_delete(
    request: Request, user: User = Depends(current_active_user)
) -> None:
    """Router dependency for /users: DELETE /users/{id} never deletes the caller."""
    if request.method != "DELETE":
        return
    try:
        target = uuid.UUID(str(request.path_params.get("id")))
    except ValueError:
        return  # the library answers 422 for it
    if target == user.id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own account"
        )
