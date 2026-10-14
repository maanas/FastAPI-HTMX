import html
import json
import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.app import app
from app.database.db import get_async_session
from app.database.security import current_active_user
from app.models.groups import Group, UserGroupLink
from app.models.users import User, UserProfile

from .error_asserts import CSRF_MESSAGE, alert_message

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
GROUP_NAME = "pytest-view-group"
USER_EMAIL = "pytest-group-view@example.com"


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def logged_in():
    user = SimpleNamespace(
        id=uuid.uuid4(), email="admin@example.com", is_superuser=True
    )
    app.dependency_overrides[current_active_user] = lambda: user
    yield user
    app.dependency_overrides.pop(current_active_user, None)


@pytest.fixture
async def created_groups(db_session):
    """Ids of the groups a test made; they are deleted by id afterwards."""
    ids = []
    yield ids
    await db_session.rollback()
    if ids:
        await db_session.execute(
            delete(UserGroupLink).where(UserGroupLink.group_id.in_(ids))
        )
        await db_session.execute(delete(Group).where(Group.id.in_(ids)))
        await db_session.commit()


@pytest.fixture
async def stored_user(db_session, created_groups):
    """A user with a profile; deleted by id after the groups and their links."""
    profile = UserProfile(first_name="Ada", last_name="Lovelace")
    db_session.add(profile)
    await db_session.flush()
    user = User(
        email=USER_EMAIL,
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        is_verified=False,
        profile_id=profile.id,
    )
    db_session.add(user)
    await db_session.commit()
    user_id, profile_id = user.id, profile.id
    yield user
    # created_groups is listed first, so its cleanup runs after this one
    await db_session.rollback()
    await db_session.execute(
        delete(UserGroupLink).where(UserGroupLink.user_id == user_id)
    )
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.execute(delete(UserProfile).where(UserProfile.id == profile_id))
    await db_session.commit()


async def make_group(db_session, created_groups, name=GROUP_NAME, desc="A test group"):
    group = Group(group_name=name, group_desc=desc)
    db_session.add(group)
    await db_session.commit()
    created_groups.append(group.id)
    return group


def assert_full_page(response):
    assert response.status_code == 200
    assert response.text.count("<nav") == 1
    assert response.text.count("<aside") == 1
    assert "HX-Request" in response.headers["vary"]


def assert_fragment(response, root=True, vary=True, status=200):
    assert response.status_code == status
    if status != 200:
        assert response.headers["X-Error-Rendered"] == "1"
    assert "<nav" not in response.text
    assert "<aside" not in response.text
    assert "<html" not in response.text
    if root:
        assert response.text.lstrip().startswith('<div id="dashboard-body"')
        assert response.text.count('id="dashboard-body"') == 1
    if vary:
        assert "HX-Request" in response.headers["vary"]


async def test_group_list_page_and_fragment(
    client, logged_in, db_session, created_groups
):
    await make_group(db_session, created_groups)
    page = await client.get("/groups")
    assert_full_page(page)
    assert 'id="dashboard-body"' in page.text
    assert GROUP_NAME in page.text
    assert ">Groups<" in page.text  # user_type keeps the admin links
    fragment = await client.get("/groups", headers=HX)
    assert_fragment(fragment)
    assert GROUP_NAME in fragment.text
    assert 'id="group-page"' in fragment.text
    assert "group_name" not in fragment.text  # the delete sends no client name
    restored = await client.get(
        "/groups", headers={**HX, "HX-History-Restore-Request": "true"}
    )
    assert_full_page(restored)


async def test_add_form_page_and_fragment(client, logged_in):
    page = await client.get("/get_create_group")
    assert_full_page(page)
    assert 'id="create-group-form"' in page.text
    fragment = await client.get("/get_create_group", headers=HX)
    assert_fragment(fragment)
    assert 'id="create-group-form"' in fragment.text


async def test_edit_form_page_and_fragment(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    url = f"/get_group/{group.id}"
    page = await client.get(url)
    assert_full_page(page)
    assert 'id="edit-group-form"' in page.text
    fragment = await client.get(url, headers=HX)
    assert_fragment(fragment)
    assert f'value="{GROUP_NAME}"' in fragment.text


async def test_allocation_form_page_and_fragment(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    url = f"/get_group_users/{group.id}"
    page = await client.get(url)
    assert_full_page(page)
    assert 'id="create-group-form"' in page.text
    fragment = await client.get(url, headers=HX)
    assert_fragment(fragment)
    assert GROUP_NAME in fragment.text


async def test_user_profile_is_a_fragment_for_every_request(
    client, logged_in, stored_user
):
    # The fragment fills a table cell, so it has no dashboard-body root and
    # no page exists for it
    url = f"/get_user_profile/{stored_user.id}"
    for headers in ({}, HX):
        response = await client.get(url, headers=headers)
        assert_fragment(response, root=False, vary=False)
        assert "Ada Lovelace" in response.text
    missing = await client.get(f"/get_user_profile/{uuid.uuid4()}")
    assert_fragment(missing, root=False, vary=False, status=404)
    assert "not found" in missing.text


async def test_error_response_follows_the_request_kind(client, logged_in):
    logged_in.is_superuser = False
    unknown = uuid.uuid4()
    urls = (
        "/groups",
        "/get_create_group",
        f"/get_group/{unknown}",
        f"/get_group_users/{unknown}",
    )
    for url in urls:
        fragment = await client.get(url, headers=HX)
        assert_fragment(fragment, root=False, status=403)
        assert "Not authorized" in fragment.text
        page = await client.get(url)
        assert page.status_code == 403
        assert page.text.count("<nav") == 1
        assert "Not authorized" in page.text
    profile = await client.get(f"/get_user_profile/{unknown}")
    assert_fragment(profile, root=False, vary=False, status=403)
    assert "Not authorized" in profile.text


async def csrf_token_from(client):
    page = await client.get("/groups", headers=HX)
    return re.search(r'"X-CSRF-Token":\s*"([^"]+)"', page.text).group(1)


async def group_names(db_session, like=GROUP_NAME + "%"):
    db_session.expire_all()
    found = await db_session.execute(
        select(Group.group_name).where(Group.group_name.like(like))
    )
    return sorted(found.scalars())


async def test_quotes_in_a_group_name_stay_escaped_in_attributes(
    client, logged_in, db_session, created_groups
):
    name = "pytest-q\"uote's"
    group = await make_group(db_session, created_groups, name=name)

    listing = await client.get("/groups", headers=HX)
    assert name not in listing.text
    assert "pytest-q&#34;uote&#39;s" in listing.text
    attr = re.search(r"id=\"group-page\".*?hx-headers='([^']*)'", listing.text, re.S)
    assert "X-CSRF-Token" in json.loads(html.unescape(attr.group(1)))

    edit = await client.get(f"/get_group/{group.id}", headers=HX)
    value = re.search(r'name="group_name".*?value="([^"]*)"', edit.text, re.S)
    assert '"' not in value.group(1)
    assert html.unescape(value.group(1)) == name


async def test_delete_needs_the_csrf_token(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    response = await client.delete(f"/delete_group/{group.id}", headers=HX)
    assert response.status_code == 403
    assert alert_message(response) == CSRF_MESSAGE
    assert await group_names(db_session) == [GROUP_NAME]


async def test_delete_names_the_database_group_not_the_client(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete_group/{group.id}",
        params={"group_name": "Spoofed name"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 200
    assert json.loads(response.headers["HX-Location"]) == {
        "path": "/groups",
        "target": "#dashboard-body",
        "swap": "outerHTML",
    }
    message = json.loads(response.headers["HX-Trigger"])["showAlert"]["message"]
    assert message == f"{GROUP_NAME} deleted successfully"
    assert "Spoofed" not in response.headers["HX-Trigger"]
    assert await group_names(db_session) == []


async def test_delete_works_without_the_client_sending_a_name(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups, desc=None)
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete_group/{group.id}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "HX-Location" in response.headers
    assert await group_names(db_session) == []


async def test_delete_is_refused_for_a_regular_user(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.delete(
        f"/delete_group/{group.id}", headers={**HX, "X-CSRF-Token": token}
    )
    assert response.status_code == 403
    assert "Not authorized" in alert_message(response)
    assert await group_names(db_session) == [GROUP_NAME]


async def test_create_adds_a_group_and_refuses_a_duplicate(
    client, logged_in, db_session, created_groups
):
    token = await csrf_token_from(client)
    data = {"group_name": GROUP_NAME, "group_desc": "A test group"}
    created = await client.post(
        "/post_create_group", data=data, headers={**HX, "X-CSRF-Token": token}
    )
    assert json.loads(created.headers["HX-Location"])["path"] == "/groups"
    db_session.expire_all()
    ids = (
        await db_session.execute(select(Group.id).where(Group.group_name == GROUP_NAME))
    ).scalars()
    created_groups.extend(ids)
    assert len(created_groups) == 1

    token = await csrf_token_from(client)  # the token changes after a write
    duplicate = await client.post(
        "/post_create_group", data=data, headers={**HX, "X-CSRF-Token": token}
    )
    assert duplicate.status_code == 409
    assert "HX-Location" not in duplicate.headers
    assert "already exists" in duplicate.text
    assert 'id="create-group-form"' in duplicate.text
    assert await group_names(db_session) == [GROUP_NAME]


async def test_create_is_refused_for_a_regular_user(
    client, logged_in, db_session, created_groups
):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.post(
        "/post_create_group",
        data={"group_name": GROUP_NAME, "group_desc": "A test group"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" not in response.headers
    assert "Not authorized" in response.text
    assert await group_names(db_session) == []


async def test_rename_to_an_existing_name_is_an_error_not_a_500(
    client, logged_in, db_session, created_groups
):
    await make_group(db_session, created_groups)
    other = await make_group(db_session, created_groups, name=GROUP_NAME + "-other")
    token = await csrf_token_from(client)
    response = await client.put(
        f"/post_update_group{other.id}",
        data={"group_name": GROUP_NAME, "group_desc": "Another group"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 409
    assert "HX-Location" not in response.headers
    assert "already exists" in response.text
    assert 'id="edit-group-form"' in response.text
    assert await group_names(db_session) == [GROUP_NAME, GROUP_NAME + "-other"]


async def test_update_keeps_the_own_name_and_redirects(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    group_id = group.id
    token = await csrf_token_from(client)
    response = await client.put(
        f"/post_update_group{group_id}",
        data={"group_name": GROUP_NAME, "group_desc": "A new description"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert json.loads(response.headers["HX-Location"])["target"] == "#dashboard-body"
    db_session.expire_all()
    desc = (
        await db_session.execute(select(Group.group_desc).where(Group.id == group_id))
    ).scalar_one()
    assert desc == "A new description"


async def test_update_without_the_token_shows_no_group_data(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups, desc="Secret description")
    response = await client.put(
        f"/post_update_group{group.id}",
        data={"group_name": "typed-name", "group_desc": "Changed"},
        headers=HX,
    )
    assert response.status_code == 403
    assert "HX-Location" not in response.headers
    assert CSRF_MESSAGE in response.text
    # The form holds what was typed; nothing stored is read for this request
    assert 'value="typed-name"' in response.text
    assert "Secret description" not in response.text
    assert GROUP_NAME not in response.text


async def test_allocation_without_the_token_shows_no_group_data(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    response = await client.post(
        f"/post_group_user_link/{group.id}", data={}, headers=HX
    )
    assert response.status_code == 403
    assert "HX-Location" not in response.headers
    assert CSRF_MESSAGE in response.text
    # The ticked boxes cannot be shown again without the user list, so a superuser
    # gets the form back (see test_form_values.py for the boxes)
    assert 'id="create-group-form"' in response.text


async def test_allocation_post_redirects_and_keeps_the_form_on_error(
    client, logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    token = await csrf_token_from(client)
    ok = await client.post(
        f"/post_group_user_link/{group.id}",
        data={"all_users": []},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert json.loads(ok.headers["HX-Location"])["path"] == "/groups"

    token = await csrf_token_from(client)  # the token changes after a write
    bad = await client.post(
        f"/post_group_user_link/{group.id}",
        data={"all_users": "not-a-uuid"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert bad.status_code == 400
    assert "HX-Location" not in bad.headers
    assert 'id="create-group-form"' in bad.text
    assert GROUP_NAME in bad.text


async def link_ids(db_session, group_id):
    db_session.expire_all()
    found = await db_session.execute(
        select(UserGroupLink.user_id).where(UserGroupLink.group_id == group_id)
    )
    return list(found.scalars())


def checkbox_checked(text, user_id):
    tag = re.search(rf'<input\s[^>]*id="user-{user_id}"[^>]*>', text, re.S).group(0)
    return "checked" in tag


async def test_a_user_is_linked_to_a_group_and_unlinked_again(
    client, logged_in, db_session, created_groups, stored_user
):
    group = await make_group(db_session, created_groups)
    group_id, user_id = group.id, stored_user.id
    url = f"/post_group_user_link/{group_id}"

    token = await csrf_token_from(client)
    linked = await client.post(
        url,
        data={"all_users": [str(user_id)], "users_selected": [str(user_id)]},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert json.loads(linked.headers["HX-Location"])["path"] == "/groups"
    assert await link_ids(db_session, group_id) == [user_id]
    form = await client.get(f"/get_group_users/{group_id}", headers=HX)
    assert checkbox_checked(form.text, user_id)

    token = await csrf_token_from(client)
    unlinked = await client.post(
        url,
        data={"all_users": [str(user_id)]},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" in unlinked.headers
    assert await link_ids(db_session, group_id) == []
    form = await client.get(f"/get_group_users/{group_id}", headers=HX)
    assert not checkbox_checked(form.text, user_id)


async def test_a_user_ticked_twice_is_linked_once(
    client, logged_in, db_session, created_groups, stored_user
):
    group = await make_group(db_session, created_groups)
    group_id, user_id = group.id, stored_user.id
    token = await csrf_token_from(client)
    response = await client.post(
        f"/post_group_user_link/{group_id}",
        data={
            "all_users": [str(user_id)],
            "users_selected": [str(user_id), str(user_id)],
        },
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" in response.headers
    assert await link_ids(db_session, group_id) == [user_id]


async def test_an_unknown_user_id_is_refused_and_nothing_is_written(
    client, logged_in, db_session, created_groups, stored_user
):
    group = await make_group(db_session, created_groups)
    group_id, user_id = group.id, stored_user.id
    token = await csrf_token_from(client)
    response = await client.post(
        f"/post_group_user_link/{group_id}",
        data={
            "all_users": [str(user_id), str(uuid.uuid4())],
            "users_selected": [str(user_id), str(uuid.uuid4())],
        },
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert "HX-Location" not in response.headers
    assert "Unknown user selected" in response.text
    assert 'id="create-group-form"' in response.text
    assert await link_ids(db_session, group_id) == []


async def test_a_name_differing_only_in_case_is_refused(
    client, logged_in, db_session, created_groups
):
    await make_group(db_session, created_groups)
    other = await make_group(db_session, created_groups, name=GROUP_NAME + "-other")
    other_id = other.id
    upper = GROUP_NAME.upper()

    token = await csrf_token_from(client)
    created = await client.post(
        "/post_create_group",
        data={"group_name": upper, "group_desc": "A test group"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" not in created.headers
    assert "already exists" in created.text

    renamed = await client.put(
        f"/post_update_group{other_id}",
        data={"group_name": upper, "group_desc": "A test group"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "HX-Location" not in renamed.headers
    assert "already exists" in renamed.text
    assert await group_names(db_session) == [GROUP_NAME, GROUP_NAME + "-other"]


async def test_deleting_a_group_with_a_linked_user_removes_the_link(
    client, logged_in, db_session, created_groups, stored_user
):
    group = await make_group(db_session, created_groups)
    group_id, user_id = group.id, stored_user.id
    db_session.add(UserGroupLink(group_id=group_id, user_id=user_id))
    await db_session.commit()

    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete_group/{group_id}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "HX-Location" in response.headers
    assert await group_names(db_session) == []
    assert await link_ids(db_session, group_id) == []


async def test_an_anonymous_request_does_not_get_the_page(client, db_session):
    app.dependency_overrides.pop(current_active_user, None)
    response = await client.get("/groups")
    assert response.status_code in (307, 401, 403)
    assert "<aside" not in response.text
    assert "Groups" not in response.text


async def test_an_error_response_logs_no_email_and_no_token(
    client, logged_in, db_session, created_groups, stored_user
):
    group = await make_group(db_session, created_groups)
    token = await csrf_token_from(client)
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="INFO")
    try:
        # The error context holds the users (with emails) and the token
        response = await client.post(
            f"/post_group_user_link/{group.id}",
            data={"all_users": "not-a-uuid"},
            headers={**HX, "X-CSRF-Token": token},
        )
    finally:
        logger.remove(sink)
    assert 'id="create-group-form"' in response.text
    logged = "\n".join(lines)
    assert "context keys" in logged
    assert USER_EMAIL not in logged
    assert token not in logged


@pytest.fixture
async def real_admin_logged_in(db_session):
    """The signed-in superuser as a real row loaded through the route's own session,
    so a rollback in the route expires it (a plain fake object cannot be)."""
    admin = User(
        email="pytest-group-admin@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
        is_verified=False,
    )
    db_session.add(admin)
    await db_session.commit()
    admin_id = admin.id

    async def load_user(session: AsyncSession = Depends(get_async_session)):
        return await session.get(User, admin_id)

    app.dependency_overrides[current_active_user] = load_user
    yield admin_id
    app.dependency_overrides.pop(current_active_user, None)
    await db_session.rollback()
    await db_session.execute(delete(User).where(User.id == admin_id))
    await db_session.commit()


async def test_a_failed_allocation_with_a_real_user_row_is_not_a_500(
    client, real_admin_logged_in, db_session, created_groups
):
    group = await make_group(db_session, created_groups)
    token = await csrf_token_from(client)
    response = await client.post(
        f"/post_group_user_link/{group.id}",
        data={"all_users": "not-a-uuid"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert "HX-Location" not in response.headers
    assert 'id="create-group-form"' in response.text
