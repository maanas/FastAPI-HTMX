from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from fastapi_csrf_protect import CsrfProtect

from app.database.security import (
    UserManager,
    current_active_user,
    get_user_manager,
    verify_jwt,
)
from app.models.users import User as UserModelDB
from app.routes.view.csrf import csrf_token_for, set_csrf_cookie
from app.templates import templates

# Create an APIRouter
login_view_route = APIRouter()


# Defining a route to navigate to the dashboard page using the current_active_user dependency
@login_view_route.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    request: Request,
    user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    csrf_token, signed_token = csrf_token_for(request, csrf_protect)

    # Access the cookies using the Request object
    cookies = request.cookies
    cookie_value = cookies.get("fastapiusersauth")
    response = templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "request": request,
            "title": "FastAPI-HTMX",
            "message": f"Welcome to FastAPI-HTMX! {user.email}",
            "cookie_value": cookie_value,
            "csrf_token": csrf_token,
            "user_type": user.is_superuser,
        },
    )
    set_csrf_cookie(csrf_protect, response, signed_token)
    return response


@login_view_route.get("/")
async def get_index(
    request: Request, user_manager: UserManager = Depends(get_user_manager)
):
    cookies = request.cookies
    cookie_value = cookies.get("fastapiusersauth")
    if cookie_value is not None:
        if await verify_jwt(cookie_value, user_manager):
            return RedirectResponse("/dashboard", status_code=302)
        else:
            return RedirectResponse("/login", status_code=302)
    else:
        return RedirectResponse("/login", status_code=302)


@login_view_route.get(
    "/login",
    summary="Gets the login page",
    tags=["Pages", "Authentication"],
    response_class=HTMLResponse,
)
async def get_login(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
):
    current_page = request.url.path.split("/")[-1]
    csrf_token, signed_token = csrf_token_for(request, csrf_protect)

    context = {
        "request": request,
        "current_page": current_page,
        "csrf_token": csrf_token,
    }

    response = templates.TemplateResponse(request, "pages/login.html", context)

    set_csrf_cookie(csrf_protect, response, signed_token)
    return response


@login_view_route.get(
    "/register",
    summary="Gets the login page",
    tags=["Pages", "Register USer"],
    response_class=HTMLResponse,
)
async def get_register(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
):
    current_page = request.url.path.split("/")[-1]
    csrf_token, signed_token = csrf_token_for(request, csrf_protect)
    context = {
        "request": request,
        "current_page": current_page,
        "csrf_token": csrf_token,
    }
    response = templates.TemplateResponse(request, "pages/register.html", context)
    set_csrf_cookie(csrf_protect, response, signed_token)
    return response
