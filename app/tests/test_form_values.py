"""A failed form post shows the form again with what the user typed: in the value
attribute, the selected option and the checked box. The stored values come back on a
GET, and the submitted ones win on an error answer."""

import re
import uuid
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import delete, update
from starlette.requests import Request

from app.app import app
from app.database.security import current_active_user
from app.models.groups import Group, UserGroupLink
from app.models.users import Role, User, UserProfile
from app.routes.view import role as role_routes
from app.routes.view.errors import (
    CSRF_MESSAGE,
    UNEXPECTED_MESSAGE,
    describe_exception,
    submitted_form,
)
from app.schema.users import RoleCreate

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
# Markup, a double quote and an ampersand in one value
TRICKY = 'a <script>x</script> "q" & b'
TRICKY_SHOWN = "a &lt;script&gt;x&lt;/script&gt; &#34;q&#34; &amp; b"
STORED_ROLE = "pytest-form-stored-role"
STORED_GROUP = "pytest-form-stored-group"
EMAIL = "pytest-form-values@example.com"


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
async def stored_role(db_session):
    role = Role(role_name=STORED_ROLE, role_desc="stored role description")
    db_session.add(role)
    await db_session.commit()
    return role


@pytest.fixture
async def stored_group(db_session):
    group = Group(group_name=STORED_GROUP, group_desc="stored group description")
    db_session.add(group)
    await db_session.commit()
    group_id = group.id
    yield group
    await db_session.rollback()
    await db_session.execute(
        delete(UserGroupLink).where(UserGroupLink.group_id == group_id)
    )
    await db_session.execute(delete(Group).where(Group.id == group_id))
    await db_session.commit()


@pytest.fixture
async def stored_user(db_session, stored_group):
    """A user with a profile, a role and a link to `stored_group`."""
    role = Role(role_name="pytest-form-user-role")
    other_role = Role(role_name="pytest-form-other-role")
    profile = UserProfile(first_name="Ada", last_name="Lovelace", gender="female")
    db_session.add_all([role, other_role, profile])
    await db_session.flush()
    user = User(
        email=EMAIL,
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        is_verified=False,
        profile_id=profile.id,
        role_id=role.id,
    )
    db_session.add(user)
    await db_session.commit()
    user_id, profile_id = user.id, profile.id
    db_session.add(UserGroupLink(group_id=stored_group.id, user_id=user_id))
    await db_session.commit()
    user.other_role = other_role
    yield user
    await db_session.rollback()
    await db_session.execute(
        delete(UserGroupLink).where(UserGroupLink.user_id == user_id)
    )
    await db_session.execute(
        update(User).where(User.id == user_id).values(role_id=None)
    )
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.execute(delete(UserProfile).where(UserProfile.id == profile_id))
    await db_session.commit()


class Controls(HTMLParser):
    """The text inputs (name -> value), checked boxes and selected options of a form."""

    def __init__(self, text):
        super().__init__()
        self.values = {}
        self.checked = []
        self.selected = {}
        self.password_or_file = []
        self._select = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input":
            kind = a.get("type", "text")
            if kind in ("password", "file") or "value" in a and kind == "password":
                self.password_or_file.append(a.get("name"))
            if kind == "checkbox" and "checked" in a:
                self.checked.append(a["value"])
            elif kind in ("text", "date") and "name" in a:
                self.values[a["name"]] = a.get("value", "")
        elif tag == "select":
            self._select = a.get("name")
        elif tag == "option" and self._select and "selected" in a:
            self.selected[self._select] = a.get("value")

    def handle_endtag(self, tag):
        if tag == "select":
            self._select = None


async def csrf_token_from(client):
    page = await client.get("/role", headers=HX)
    return re.search(r'"X-CSRF-Token":\s*"([^"]+)"', page.text).group(1)


async def send(client, method, url, data, token=True):
    headers = dict(HX)
    if token:
        headers["X-CSRF-Token"] = await csrf_token_from(client)
    return await getattr(client, method)(url, data=data, headers=headers)


# --- add forms

ADD_FORMS = [
    ("/post_create_roles", "role_name", "role_desc"),
    ("/post_create_group", "group_name", "group_desc"),
]


@pytest.mark.parametrize("url, name, desc", ADD_FORMS)
@pytest.mark.parametrize("token", [True, False], ids=["validation", "csrf"])
async def test_an_add_form_keeps_what_was_typed(
    client, logged_in, url, name, desc, token
):
    response = await send(client, "post", url, {name: "x", desc: "typed text"}, token)
    assert response.status_code == (422 if token else 403)
    controls = Controls(response.text)
    assert controls.values == {name: "x", desc: "typed text"}


@pytest.mark.parametrize("url, name, desc", ADD_FORMS)
async def test_an_add_form_shows_a_tricky_value_escaped_once(
    client, logged_in, url, name, desc
):
    response = await send(client, "post", url, {name: "x", desc: TRICKY})
    assert response.status_code == 422
    assert f'value="{TRICKY_SHOWN}"' in response.text
    assert "<script>x" not in response.text
    assert "&amp;amp;" not in response.text
    assert Controls(response.text).values[desc] == TRICKY


@pytest.mark.parametrize("url, name, desc", ADD_FORMS)
async def test_a_password_a_file_and_the_token_are_not_shown_again(
    client, logged_in, url, name, desc
):
    token = await csrf_token_from(client)
    response = await client.post(
        url,
        data={
            name: "x",
            desc: "typed",
            "password": "hunter2-secret",
            "csrf_token": "submitted-token-4711",
        },
        files={"upload": ("secret-name.txt", b"file-content-9982")},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 422
    for hidden in ("hunter2-secret", "submitted-token-4711", "file-content-9982"):
        assert hidden not in response.text
    assert not Controls(response.text).password_or_file


async def test_submitted_form_leaves_out_files_passwords_and_the_token():
    body = (
        b'--b\r\nContent-Disposition: form-data; name="a"\r\n\r\none\r\n'
        b'--b\r\nContent-Disposition: form-data; name="Password2"\r\n\r\npw\r\n'
        b'--b\r\nContent-Disposition: form-data; name="csrf_token"\r\n\r\nt\r\n'
        b'--b\r\nContent-Disposition: form-data; name="f"; filename="x.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\ndata\r\n--b--\r\n"
    )

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "headers": [(b"content-type", b"multipart/form-data; boundary=b")],
        },
        receive,
    )
    assert await submitted_form(request) == {"a": "one"}


# --- edit forms


@pytest.mark.parametrize("token", [True, False], ids=["validation", "csrf"])
async def test_the_role_edit_form_shows_the_submitted_values_not_the_stored_ones(
    client, logged_in, stored_role, token
):
    url = f"/get_role/{stored_role.id}"
    stored = Controls((await client.get(url, headers=HX)).text)
    assert stored.values == {
        "role_name": STORED_ROLE,
        "role_desc": "stored role description",
    }
    response = await send(
        client,
        "put",
        f"/post_update_role/{stored_role.id}",
        {"role_name": "x", "role_desc": TRICKY},
        token,
    )
    assert response.status_code == (422 if token else 403)
    assert Controls(response.text).values == {"role_name": "x", "role_desc": TRICKY}
    assert f'value="{TRICKY_SHOWN}"' in response.text
    assert "&amp;amp;" not in response.text


@pytest.mark.parametrize("token", [True, False], ids=["validation", "csrf"])
async def test_the_group_edit_form_shows_the_submitted_values_not_the_stored_ones(
    client, logged_in, stored_group, token
):
    stored = Controls(
        (await client.get(f"/get_group/{stored_group.id}", headers=HX)).text
    )
    assert stored.values["group_name"] == STORED_GROUP
    response = await send(
        client,
        "put",
        f"/post_update_group/{stored_group.id}",
        {"group_name": "x", "group_desc": TRICKY},
        token,
    )
    assert response.status_code == (422 if token else 403)
    assert Controls(response.text).values == {"group_name": "x", "group_desc": TRICKY}
    assert f'value="{TRICKY_SHOWN}"' in response.text


async def test_a_duplicate_name_keeps_the_typed_description(
    client, logged_in, stored_role, db_session
):
    other = Role(role_name="pytest-form-other", role_desc="other description")
    db_session.add(other)
    await db_session.commit()
    response = await send(
        client,
        "put",
        f"/post_update_role/{other.id}",
        {"role_name": STORED_ROLE, "role_desc": "typed description"},
    )
    assert response.status_code == 409
    assert Controls(response.text).values == {
        "role_name": STORED_ROLE,
        "role_desc": "typed description",
    }


async def test_a_refused_user_gets_no_stored_row_back(client, logged_in, stored_role):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.put(
        f"/post_update_role/{stored_role.id}",
        data={"role_name": "x", "role_desc": "typed"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 403
    assert STORED_ROLE not in response.text
    assert "<input" not in response.text


EDIT_USER_FORM = {
    "first_name": "Grace",
    "last_name": 'Hopper "Amazing" & <b>co</b>',
    "gender": "other",
    "dob": "31/12/1999",
    "address": "1 Main St",
    "city": "Arlington",
    "country": "USA",
    "phone": "+1 555 0100",
    "company": "Navy",
}


@pytest.mark.parametrize("token", [True, False], ids=["validation", "csrf"])
async def test_the_user_edit_form_keeps_inputs_selects_and_dates(
    client, logged_in, stored_user, token
):
    stored = Controls(
        (await client.get(f"/get_user/{stored_user.id}", headers=HX)).text
    )
    assert stored.values["first_name"] == "Ada"
    assert stored.selected["gender"] == "female"
    assert stored.selected["role_id"] == str(stored_user.role_id)

    data = {**EDIT_USER_FORM, "role_id": str(stored_user.other_role.id)}
    response = await send(
        client, "put", f"/post_update_user/{stored_user.id}", data, token
    )
    assert response.status_code == (422 if token else 403)
    controls = Controls(response.text)
    for name, value in EDIT_USER_FORM.items():
        if name != "gender":
            assert controls.values[name] == value, name
    assert controls.selected["gender"] == "other"
    assert controls.selected["role_id"] == str(stored_user.other_role.id)
    assert "<b>co</b>" not in response.text
    assert "&amp;amp;" not in response.text


# --- group user allocation


async def test_the_allocation_form_shows_the_submitted_boxes(
    client, logged_in, stored_group, stored_user
):
    url = f"/get_group_users/{stored_group.id}"
    assert Controls((await client.get(url, headers=HX)).text).checked == [
        str(stored_user.id)
    ]
    # Unticked on the form while stored as linked; an unknown id makes it fail
    data = {"all_users": [str(stored_user.id), str(uuid.uuid4())]}
    response = await send(
        client, "post", f"/post_group_user_link/{stored_group.id}", data
    )
    assert response.status_code == 400
    assert Controls(response.text).checked == []

    # Ticked on the form: the ticked box stays ticked after a failed CSRF check
    data = {
        "all_users": [str(stored_user.id)],
        "users_selected": [str(stored_user.id)],
    }
    response = await send(
        client, "post", f"/post_group_user_link/{stored_group.id}", data, token=False
    )
    assert response.status_code == 403
    assert Controls(response.text).checked == [str(stored_user.id)]


async def test_the_allocation_form_shows_a_ticked_box_that_is_not_stored(
    client, logged_in, stored_group, stored_user, db_session
):
    await db_session.execute(
        delete(UserGroupLink).where(UserGroupLink.group_id == stored_group.id)
    )
    await db_session.commit()
    data = {
        "all_users": [str(stored_user.id), str(uuid.uuid4())],
        "users_selected": [str(stored_user.id)],
    }
    response = await send(
        client, "post", f"/post_group_user_link/{stored_group.id}", data
    )
    assert response.status_code == 400
    assert Controls(response.text).checked == [str(stored_user.id)]


# --- a caller who is not a superuser gets no stored data back

DISTINCT = {
    "first_name": "Zorblax",
    "last_name": "Quimbyson",
    "city": "Distinctville",
    "company": "Distinctco",
    "address": "77 Distinct Lane",
}


@pytest.mark.parametrize("token", [True, False], ids=["token", "no-token"])
@pytest.mark.parametrize(
    "method, path",
    [
        ("put", "/post_update_role/{role}"),
        ("put", "/post_update_group/{group}"),
        ("post", "/post_group_user_link/{group}"),
        ("put", "/post_update_user/{user}"),
    ],
)
async def test_a_normal_user_gets_no_stored_data_from_a_write_route(
    client,
    logged_in,
    stored_role,
    stored_group,
    stored_user,
    db_session,
    method,
    path,
    token,
):
    await db_session.execute(
        update(UserProfile)
        .where(UserProfile.id == stored_user.profile_id)
        .values(**DISTINCT)
    )
    await db_session.commit()
    headers = dict(HX)
    if token:
        headers["X-CSRF-Token"] = await csrf_token_from(client)
    logged_in.is_superuser = False
    url = path.format(role=stored_role.id, group=stored_group.id, user=stored_user.id)
    response = await getattr(client, method)(
        url,
        data={"role_name": "x", "group_name": "x", "all_users": [str(stored_user.id)]},
        headers=headers,
    )
    assert response.status_code == 403
    # The reason: the role check when a token was sent, the CSRF check when not
    assert ("Not authorized" in response.text) is token
    assert (CSRF_MESSAGE in response.text) is not token
    stored = [
        STORED_ROLE,
        "pytest-form-user-role",
        "stored role description",
        STORED_GROUP,
        "stored group description",
        EMAIL,
        *DISTINCT.values(),
        str(stored_user.id),
    ]
    for value in stored:
        assert value not in response.text, value
    assert '<input type="checkbox"' not in response.text


# --- the hardening of the error path


class SilentFailure(Exception):
    def __str__(self):
        raise RuntimeError("no text")


def test_describe_exception_falls_back_to_the_type_name():
    assert describe_exception(SilentFailure()) == "SilentFailure"
    assert describe_exception(ValueError("kept")) == "ValueError: kept"


async def test_an_exception_whose_text_raises_still_gives_the_fixed_answer(
    client, logged_in, monkeypatch
):
    async def boom(*args, **kwargs):
        raise SilentFailure()

    monkeypatch.setattr(role_routes.role_crud, "create", boom)
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="ERROR")
    try:
        response = await send(
            client,
            "post",
            "/post_create_roles",
            {"role_name": "pytest-silent", "role_desc": "valid description"},
        )
    finally:
        logger.remove(sink)
    assert response.status_code == 500
    assert UNEXPECTED_MESSAGE in response.text
    assert "SilentFailure" in "".join(lines)


async def test_a_validation_error_in_the_chain_logs_its_type_only(
    client, logged_in, monkeypatch
):
    with pytest.raises(ValidationError) as caught:
        RoleCreate(role_name="x", role_desc="valid description")
    assert "input_value=" in str(caught.value)  # the text a log would carry

    async def boom(*args, **kwargs):
        try:
            raise caught.value
        except ValidationError as err:
            raise RuntimeError("could not save") from err

    monkeypatch.setattr(role_routes.role_crud, "create", boom)
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="ERROR")
    try:
        response = await send(
            client,
            "post",
            "/post_create_roles",
            {"role_name": "pytest-chain", "role_desc": "valid description"},
        )
    finally:
        logger.remove(sink)
    log = "".join(lines)
    assert response.status_code == 500
    assert "ValidationError" in log
    assert "input_value=" not in log
