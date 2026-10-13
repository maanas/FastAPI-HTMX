import json
import uuid

import nh3
from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy import select

from app.database.db import CurrentAsyncSession
from app.database.security import current_active_user
from app.models.groups import Group as GroupModelDB
from app.models.groups import UserGroupLink as UserGroupLinkModelDB
from app.models.users import Role as UserRoleModelDB
from app.models.users import User as UserModelDB
from app.models.users import UserProfile as UserProfileModelDB
from app.routes.view.errors import handle_error
from app.routes.view.fragments import render_view
from app.routes.view.view_crud import SQLAlchemyCRUD
from app.schema.group import GroupCreate
from app.schema.group import GroupUserLink as GroupUserLinkCreate
from app.templates import templates

group_view_route = APIRouter()

# Fragments (no layout) and the pages that include them, see fragments.py
GROUP_LIST = "partials/group/groups.html"
GROUP_ADD = "partials/group/add_group.html"
GROUP_EDIT = "partials/group/edit_group.html"
GROUP_USERS = "partials/group/add_group_user.html"
GROUP_USER_PROFILE = "partials/group/group_user_profile.html"
# Navigation that replaces the content area, as the sidebar link does
HX_LOCATION_GROUPS = json.dumps(
    {"path": "/groups", "target": "#dashboard-body", "swap": "outerHTML"}
)


group_crud = SQLAlchemyCRUD[GroupModelDB](
    GroupModelDB, related_models={UserModelDB: "users"}
)
user_crud = SQLAlchemyCRUD[UserModelDB](
    UserModelDB,
    related_models={UserProfileModelDB: "profile", UserRoleModelDB: "role"},
)


# Defining a route to navigate to the group page
@group_view_route.get("/groups", response_class=HTMLResponse)
async def get_groups(
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
        groups = await group_crud.read_all(db, skip, limit, join_relationships=True)

        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

        response = render_view(
            request,
            "pages/groups.html",
            GROUP_LIST,
            {
                "request": request,
                "groups": groups,
                "user_type": current_user.is_superuser,
                "csrf_token": csrf_token,
            },
        )

        csrf_protect.set_csrf_cookie(signed_token, response)

        return response
    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/groups.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_LIST,
        )


# Defining a route to get the user profile based on id
# Its fragment fills one table cell, not the whole content area, so every
# request gets the fragment and there is no page for it
@group_view_route.get("/get_user_profile/{user_id}", response_class=HTMLResponse)
async def get_user_profile(
    request: Request,
    user_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
):
    try:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        user_profile = await user_crud.read_by_primary_key(
            db, user_id, join_relationships=True
        )
        return templates.TemplateResponse(
            request,
            GROUP_USER_PROFILE,
            {
                "request": request,
                "user_profile": user_profile,
                "user_type": current_user.is_superuser,
            },
        )
    except Exception as e:
        # No page for this fragment: handle_error renders its template as given
        return handle_error(
            GROUP_USER_PROFILE,
            {
                "request": request,
                "user_type": current_user.is_superuser,
            },
            e,
        )


# Defining a route to add a new group to the database
@group_view_route.get("/get_create_group", response_class=HTMLResponse)
async def get_create_group(
    request: Request,
    current_user: UserModelDB = Depends(current_active_user),
):
    try:
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        csrf_token = request.headers.get("X-CSRF-Token")

        return render_view(
            request,
            "pages/group_add.html",
            GROUP_ADD,
            {
                "request": request,
                "user_type": current_user.is_superuser,
                "csrf_token": csrf_token,
            },
        )
    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/group_add.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_ADD,
        )


# Route to get the group by ID
@group_view_route.get("/get_group/{group_id}", response_class=HTMLResponse)
async def get_group_by_id(
    request: Request,
    group_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
):
    group = None
    try:
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        group = await group_crud.read_by_primary_key(db, group_id)

        csrf_token = request.headers.get("X-CSRF-Token")

        return render_view(
            request,
            "pages/group_edit.html",
            GROUP_EDIT,
            {
                "request": request,
                "group": group,
                "user_type": current_user.is_superuser,
                "csrf_token": csrf_token,
            },
        )
    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/group_edit.html",
            {
                "request": request,
                "group": group,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_EDIT,
        )


def name_is_taken(existing, group_id: uuid.UUID | None = None) -> bool:
    """True if `read_by_column` found a group other than `group_id`.

    It returns None, one group or a list when names differ only in case.
    """
    found = existing if isinstance(existing, list) else [existing]
    return any(group and group.id != group_id for group in found)


@group_view_route.post("/post_create_group", response_class=HTMLResponse)
async def post_create_group(
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
            raise HTTPException(status_code=403, detail="Not authorized to add groups")

        form = await request.form()

        # Iterate over the form fields and sanitize the values before validating against the Pydantic model
        group_create = GroupCreate(
            group_name=nh3.clean(str(form.get("group_name"))),
            group_desc=nh3.clean(str(form.get("group_desc"))),
        )

        existing_group = await group_crud.read_by_column(
            db, "group_name", group_create.group_name
        )

        if name_is_taken(existing_group):
            raise HTTPException(status_code=400, detail="Group name already exists")
        await group_crud.create(dict(group_create), db)

        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

        # Redirecting to the groups page upon successful group creation
        headers = {
            "HX-Location": HX_LOCATION_GROUPS,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "added",
                        "message": "Group added successfully",
                        "source": "group-page",
                    }
                }
            ),
            "csrf_token": csrf_token,
        }

        response = HTMLResponse(content="", headers=headers)

        # UnSetting the CSRF cookie
        csrf_protect.unset_csrf_cookie(response)

        # Setting a new CSRF cookie for validation by post future requests
        csrf_protect.set_csrf_cookie(signed_token, response)

        return response

    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/group_add.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_ADD,
        )


# Route to update a group
@group_view_route.put("/post_update_group{group_id}", response_class=HTMLResponse)
async def post_update_group(
    request: Request,
    response: Response,
    group_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    group = None
    try:
        await csrf_protect.validate_csrf(request)
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        # Kept for the error response, which shows the form again
        group = await group_crud.read_by_primary_key(db, group_id)

        form = await request.form()

        # Iterate over the form fields and sanitize the values before validating against the Pydantic model
        group_update = GroupCreate(
            group_name=nh3.clean(str(form.get("group_name"))),
            group_desc=nh3.clean(str(form.get("group_desc"))),
        )

        # Reject a name another group has: a unique violation would leave the
        # session unusable for the error response
        existing_group = await group_crud.read_by_column(
            db, "group_name", group_update.group_name
        )
        if name_is_taken(existing_group, group_id):
            raise HTTPException(status_code=400, detail="Group name already exists")

        await group_crud.update(db, group_id, dict(group_update))

        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

        # Redirecting to the groups page upon successful group update
        headers = {
            "HX-Location": HX_LOCATION_GROUPS,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "updated",
                        "message": "Group updated successfully",
                        "source": "group-page",
                    }
                }
            ),
            "csrf_token": csrf_token,
        }
        response = HTMLResponse(content="", headers=headers)

        csrf_protect.unset_csrf_cookie(response)

        csrf_protect.set_csrf_cookie(signed_token, response)

        return response
    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/group_edit.html",
            {
                "request": request,
                "group": group,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_EDIT,
        )


# Route to delete a group
@group_view_route.delete("/delete_group/{group_id}", response_class=HTMLResponse)
async def delete_group(
    request: Request,
    group_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    try:
        await csrf_protect.validate_csrf(request)

        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        # The name for the alert comes from the row, not from the client
        group_to_delete = await group_crud.read_by_primary_key(db, group_id)
        group_name = group_to_delete.group_name
        await group_crud.delete(db, group_id)

        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

        headers = {
            "HX-Location": HX_LOCATION_GROUPS,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "deleted",
                        "message": f"{group_name} deleted successfully",
                        "source": "group-page",
                    }
                }
            ),
        }
        response = HTMLResponse(content="", headers=headers)

        csrf_protect.unset_csrf_cookie(response)

        csrf_protect.set_csrf_cookie(signed_token, response)

        return response
    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/groups.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_LIST,
        )


"""
# Group Users Allocation Routes
"""


async def read_allocation(db: CurrentAsyncSession, group_id: uuid.UUID):
    """The group, all users and the ids of the users already in the group."""
    group = await group_crud.read_by_primary_key(db, group_id)
    users = await user_crud.read_all(db, join_relationships=True)
    linked = await db.execute(
        select(UserGroupLinkModelDB.user_id).where(
            UserGroupLinkModelDB.group_id == group_id
        )
    )
    return group, users, list(linked.scalars().all())


# Defining a route getting the page for allocating users to the selected group
@group_view_route.get("/get_group_users/{group_id}", response_class=HTMLResponse)
async def get_group_users(
    request: Request,
    group_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
):
    group = None
    try:
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        group, users, group_user_ids = await read_allocation(db, group_id)

        csrf_token = request.headers.get("X-CSRF-Token")
        return render_view(
            request,
            "pages/group_users.html",
            GROUP_USERS,
            {
                "request": request,
                "group": group,
                "users": users,
                "group_user_ids": group_user_ids,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
        )
    except Exception as e:
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/group_users.html",
            {
                "request": request,
                "group": group,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_USERS,
        )


# Update the UserGroupLink model based on selected user for a group
@group_view_route.post("/post_group_user_link/{group_id}", response_class=HTMLResponse)
async def post_group_user_link(
    request: Request,
    response: Response,
    group_id: uuid.UUID,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    checked = False
    try:
        await csrf_protect.validate_csrf(request)
        # checking the current user as super user
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to add groups")
        checked = True
        group, users, group_user_ids = await read_allocation(db, group_id)
        form = await request.form()

        all_users = set(form.getlist("all_users"))
        # A user ticked twice must not be linked twice
        selected_list = list(dict.fromkeys(form.getlist("users_selected")))
        selected_users = set(selected_list)

        # Refuse an id that is no user before anything is written
        submitted = {uuid.UUID(str(user_id)) for user_id in all_users | selected_users}
        known = await db.execute(
            select(UserModelDB.id).where(UserModelDB.id.in_(submitted))
        )
        if submitted - set(known.scalars().all()):
            raise HTTPException(status_code=400, detail="Unknown user selected")

        # Removing the users already selected from the list of all users
        non_selected_users = all_users - selected_users
        db_data = []
        for user_id in selected_list:
            group_user_link = GroupUserLinkCreate(
                group_id=uuid.UUID(nh3.clean(str(group_id))),
                user_id=uuid.UUID(nh3.clean(str(user_id))),
            )
            group_id = group_user_link.group_id
            user_id = group_user_link.user_id
            existing_record = await db.scalar(
                select(UserGroupLinkModelDB).filter_by(
                    group_id=group_id, user_id=user_id
                )
            )
            if existing_record:
                print(f"Record with {user_id} already exists")
            else:
                db_data.append(
                    group_user_link.model_dump(exclude={"id"}, exclude_unset=True)
                )
        for user_id in non_selected_users:
            group_user_link = GroupUserLinkCreate(
                group_id=uuid.UUID(nh3.clean(str(group_id))),
                user_id=uuid.UUID(nh3.clean(str(user_id))),
            )
            group_id = group_user_link.group_id
            user_id = group_user_link.user_id
            existing_record = await db.scalar(
                select(UserGroupLinkModelDB).filter_by(
                    group_id=group_id, user_id=user_id
                )
            )
            if existing_record:
                await db.delete(existing_record)
                await db.commit()

        if len(db_data) > 0:
            db.add_all([UserGroupLinkModelDB(**link) for link in db_data])
            await db.commit()

        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

        headers = {
            "HX-Location": HX_LOCATION_GROUPS,
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "added",
                        "message": "User allocated to Group successfully",
                        "source": "group-page",
                    }
                }
            ),
            "csrf_token": csrf_token,
        }

        response = HTMLResponse(content="", headers=headers)

        csrf_protect.unset_csrf_cookie(response)

        csrf_protect.set_csrf_cookie(signed_token, response)

        return response
    except Exception as e:
        # A failed write leaves the session unusable: start over and read the
        # form again; if that fails too, the response is the error alone.
        # Nothing is read for a request that failed the CSRF or superuser check.
        group, users, group_user_ids = None, [], []
        if checked:
            try:
                await db.rollback()
                group, users, group_user_ids = await read_allocation(db, group_id)
            except Exception:
                pass
        csrf_token = request.headers.get("X-CSRF-Token")
        return handle_error(
            "pages/group_users.html",
            {
                "request": request,
                "group": group,
                "users": users,
                "group_user_ids": group_user_ids,
                "csrf_token": csrf_token,
                "user_type": current_user.is_superuser,
            },
            e,
            fragment=GROUP_USERS,
        )
