# importing the required modules
import json
import uuid

import nh3
from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

from app.database.db import CurrentAsyncSession
from app.database.security import current_active_user
from app.models.users import Role as RoleModelDB
from app.models.users import User as UserModelDB
from app.routes.view.csrf import csrf_token_for, set_csrf_cookie
from app.routes.view.errors import (
    alert_error,
    handle_error,
    stub_row,
    submitted_form,
)
from app.routes.view.fragments import CONTENT_TARGET_ID, render_view, wants_fragment
from app.routes.view.view_crud import SQLAlchemyCRUD
from app.schema.users import RoleCreate

role_view_route = APIRouter()

# Fragments (no layout) and the pages that include them, see fragments.py
ROLE_LIST = "partials/role/role_list.html"
ROLE_ADD = "partials/role/add_role.html"
ROLE_EDIT = "partials/role/edit_role.html"
# Navigation that replaces the content area, as the sidebar link does
HX_LOCATION_ROLES = json.dumps(
    {"path": "/role", "target": f"#{CONTENT_TARGET_ID}", "swap": "outerHTML"}
)


role_crud = SQLAlchemyCRUD[RoleModelDB](RoleModelDB)


# Defining a view route to navigate to the role page
@role_view_route.get("/role", response_class=HTMLResponse)
async def get_role(
    request: Request,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    skip: int = 0,
    limit: int = 100,
    csrf_protect: CsrfProtect = Depends(),
):
    try:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to view this page"
            )
        # Access the cookies using the Request object
        roles = await role_crud.read_all(db, skip, limit)
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = render_view(
            request,
            "pages/role.html",
            ROLE_LIST,
            {
                "request": request,
                "roles": roles,
                "user_type": current_user.is_superuser,
                "csrf_token": csrf_token,
            },
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response
    except Exception as e:
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/role.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=ROLE_LIST,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


# Defining a get view route for showing form to add a new role to the database
@role_view_route.get("/get_create_roles", response_class=HTMLResponse)
async def get_create_roles(
    request: Request,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    # checking the current user as super user
    try:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add roles")
        # Redirecting to the add role page upon successful role creation

        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = render_view(
            request,
            "pages/role_add.html",
            ROLE_ADD,
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response
    except Exception as e:
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/role_add.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=ROLE_ADD,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


# Defining a post view route for adding a new role to the database
@role_view_route.post("/post_create_roles", response_class=HTMLResponse)
async def post_create_roles(
    request: Request,
    response: Response,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    try:

        await csrf_protect.validate_csrf(request)
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add roles")

        form = await request.form()

        # Iterate over the form fields and sanitize the values before validating against the Pydantic model
        role_create = RoleCreate(
            role_name=nh3.clean(str(form.get("role_name"))),
            role_desc=nh3.clean(str(form.get("role_desc"))),
        )

        existing_role = await role_crud.read_by_column(
            db, "role_name", role_create.role_name
        )

        if existing_role:
            raise HTTPException(status_code=409, detail="Role name already exists")
        await role_crud.create(dict(role_create), db)

        # Redirecting to the add role page upon successful role creation
        headers = {
            "HX-Location": HX_LOCATION_ROLES,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "added",
                        "message": f"{role_create.role_name} added successfully",
                        "source": "role-page",
                    },
                }
            ),
            "HX-Push-Url": "true",
        }

        response = HTMLResponse(content="", headers=headers)

        return response
    except Exception as e:
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/role_add.html",
            {
                "request": request,
                "form": await submitted_form(request),
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=ROLE_ADD,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


# Defining end point to get the record based on the id
@role_view_route.get("/get_role/{role_id}", response_class=HTMLResponse)
async def get_role_by_id(
    request: Request,
    role_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    role = None
    try:
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add roles")
        role = await role_crud.read_by_primary_key(db, role_id)

        csrf_token, signed_token = csrf_token_for(request, csrf_protect)

        response = render_view(
            request,
            "pages/role_edit.html",
            ROLE_EDIT,
            {
                "request": request,
                "role": role,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response
    except Exception as e:
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/role_edit.html",
            {
                "request": request,
                "role": role,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=ROLE_EDIT,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


# Defining end point to update the record based on the id
@role_view_route.put("/post_update_role/{role_id}", response_class=HTMLResponse)
async def post_update_role(
    request: Request,
    response: Response,
    role_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    # Read once: the rollback in the error path expires the user object
    is_superuser = current_user.is_superuser
    role = None
    try:
        await csrf_protect.validate_csrf(request)
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add roles")
        # Kept for the error response, which shows the form again
        role = await role_crud.read_by_primary_key(db, role_id)

        form = await request.form()

        # Iterate over the form fields and sanitize the values before validating against the Pydantic model
        role_update = RoleCreate(
            role_name=nh3.clean(str(form.get("role_name"))),
            role_desc=nh3.clean(str(form.get("role_desc"))),
        )

        # Reject a name another role has: a unique violation would leave the
        # session unusable for the error response
        existing_role = await role_crud.read_by_column(
            db, "role_name", role_update.role_name
        )
        if existing_role and existing_role.id != role_id:
            raise HTTPException(status_code=409, detail="Role name already exists")

        await role_crud.update(db, role_id, dict(role_update))

        # Redirecting to the add role page upon successful role creation
        headers = {
            "HX-Location": HX_LOCATION_ROLES,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "updated",
                        "message": f"{role_update.role_name} updated successfully",
                        "source": "role-page",
                    },
                }
            ),
            "HX-Boost": "true",
        }
        response = HTMLResponse(content="", headers=headers)

        return response
    except Exception as e:
        # A request stopped by the CSRF check has not read the row: the form is
        # shown again with what was typed, and no stored value (only to a superuser)
        if isinstance(e, CsrfProtectError) and is_superuser:
            role = stub_row(role_id, role_name="", role_desc="")
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/role_edit.html",
            {
                "request": request,
                "role": role,
                "form": await submitted_form(request),
                "csrf_token": csrf_token,
                "user_type": is_superuser,
            },
            e,
            fragment=ROLE_EDIT,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


# Defining a route to delete the record based on the id
@role_view_route.delete("/delete_role/{role_id}", response_class=HTMLResponse)
async def delete_role(
    request: Request,
    role_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    try:
        await csrf_protect.validate_csrf(request)
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete roles"
            )
        # The name for the alert comes from the row, not from the client
        role_to_delete = await role_crud.read_by_primary_key(db, role_id)
        role_name = role_to_delete.role_name
        await role_crud.delete(db, role_id)

        headers = {
            "HX-Location": HX_LOCATION_ROLES,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "deleted",
                        "message": f"{role_name} deleted successfully",
                        "source": "role-page",
                    },
                }
            ),
            "HX-Boost": "true",
        }

        response = HTMLResponse(content="", headers=headers)

        return response
    except Exception as e:
        # The list stays; the refusal shows as an alert above it
        if wants_fragment(request):
            return alert_error(e, "role-page")
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/role.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=ROLE_LIST,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response
