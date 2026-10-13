import html
import json
import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi import Depends, HTTPException, Request
from httpx import ASGITransport, AsyncClient
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.app import app
from app.core.security_headers import SECURITY_HEADERS
from app.database.db import get_async_session
from app.database.security import current_active_user
from app.models.upload import Upload
from app.models.users import User
from app.routes.view import upload as upload_routes
from app.tests.template_rules import template_rule_violations

pytestmark = pytest.mark.anyio

HX = {"HX-Request": "true"}
STORAGE_UNAVAILABLE = upload_routes.STORAGE_UNAVAILABLE
USER_EMAIL = "pytest-upload-view@example.com"
FILE_NAME = "pytest-report.txt"
NASTY_NAME = "pytest-q\"uote's<script>alert(1)</script>.txt"


class FakeMinio:
    """Stands in for the MinIO client: objects live in a dict.

    Like the real one it returns an "Error occurred" string instead of raising.
    """

    def __init__(self):
        self.objects = {}
        self.fail_upload = False
        self.fail_remove = False
        self.raise_error = None

    async def upload_file(self, file, object_name):
        if self.raise_error:
            raise self.raise_error
        if self.fail_upload:
            return "Error occurred: S3 operation failed"
        self.objects[object_name] = await file.read()
        return f"http://minio.test/bucket/{object_name}"

    async def get_file(self, object_name):
        if self.raise_error:
            raise self.raise_error
        if object_name not in self.objects:
            return "Error occurred: S3 operation failed; code: NoSuchKey"
        return iter([self.objects[object_name]])

    async def remove_file(self, object_name):
        if self.raise_error:
            raise self.raise_error
        if self.fail_remove:
            return "Error occurred: S3 operation failed"
        self.objects.pop(object_name, None)
        return f"File '{object_name}' removed successfully"


@pytest.fixture
def fake_minio(monkeypatch):
    fake = FakeMinio()
    monkeypatch.setattr(upload_routes, "minio", fake)
    return fake


@pytest.fixture
async def client(anyio_backend):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
async def stored_user(db_session):
    """The user the uploads belong to (a foreign key); files go first, by id."""
    user = User(
        email=USER_EMAIL,
        hashed_password="x",
        is_active=True,
        is_superuser=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    user_id = user.id
    yield user
    await db_session.rollback()
    await db_session.execute(delete(Upload).where(Upload.user_id == user_id))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.commit()


@pytest.fixture
async def other_user(db_session, stored_user):
    """A second user (user B) whose files user A must not reach."""
    user = User(
        email="pytest-upload-other@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    user_id = user.id
    yield user
    await db_session.rollback()
    await db_session.execute(delete(Upload).where(Upload.user_id == user_id))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.commit()


@pytest.fixture
def logged_in(stored_user):
    user = SimpleNamespace(id=stored_user.id, email=USER_EMAIL, is_superuser=True)
    app.dependency_overrides[current_active_user] = lambda: user
    yield user
    app.dependency_overrides.pop(current_active_user, None)


async def make_file(db_session, user, name=FILE_NAME):
    row = Upload(
        name=name,
        unique_name=f"{uuid.uuid4()}.txt",
        file_type="text/plain",
        source="upload-page",
        file_size=5,
        user_id=user.id,
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def stored_names(db_session, user_id):
    db_session.expire_all()
    found = await db_session.execute(
        select(Upload.name).where(Upload.user_id == user_id)
    )
    return sorted(found.scalars())


def assert_full_page(response):
    assert response.status_code == 200
    assert response.text.count("<nav") == 1
    assert response.text.count("<aside") == 1
    assert "HX-Request" in response.headers["vary"]


def assert_fragment(response, root=True):
    assert response.status_code == 200
    assert "<nav" not in response.text
    assert "<aside" not in response.text
    assert "<html" not in response.text
    if root:
        assert response.text.lstrip().startswith('<div id="dashboard-body"')
        assert response.text.count('id="dashboard-body"') == 1


async def csrf_token_from(client):
    page = await client.get("/uploads", headers=HX)
    return re.search(r'"X-CSRF-Token":\s*"([^"]+)"', page.text).group(1)


async def test_upload_page_and_fragment(client, logged_in, db_session, stored_user):
    await make_file(db_session, stored_user)
    page = await client.get("/uploads")
    assert_full_page(page)
    assert 'id="upload-form"' in page.text
    assert FILE_NAME in page.text
    assert 'src="/static/js/upload.js"' in page.text
    fragment = await client.get("/uploads", headers=HX)
    assert_fragment(fragment)
    assert "HX-Request" in fragment.headers["vary"]
    assert FILE_NAME in fragment.text
    assert 'id="upload-files-table"' in fragment.text
    assert fragment.text.count('id="upload-files-table"') == 1
    restored = await client.get(
        "/uploads", headers={**HX, "HX-History-Restore-Request": "true"}
    )
    assert_full_page(restored)


async def test_files_table_is_a_fragment_for_every_request(
    client, logged_in, db_session, stored_user
):
    await make_file(db_session, stored_user)
    for headers in ({}, HX):
        response = await client.get("/get_uploaded_files", headers=headers)
        assert_fragment(response, root=False)
        assert FILE_NAME in response.text
        assert "<table" not in response.text


async def test_error_response_follows_the_request_kind(client, logged_in):
    logged_in.is_superuser = False
    fragment = await client.get("/uploads", headers=HX)
    assert_fragment(fragment, root=False)
    assert "Not authorized" in fragment.text
    page = await client.get("/uploads")
    assert page.text.count("<nav") == 1
    assert "Not authorized" in page.text
    table = await client.get("/get_uploaded_files", headers=HX)
    assert "Not authorized" in table.text
    assert "<nav" not in table.text


def test_the_rule_helper_flags_hx_on_attributes():
    assert template_rule_violations('<form hx-on::after-request="x()"></form>')
    assert template_rule_violations('<div hx-on:click="x()"></div>')
    assert template_rule_violations('<div hx-on="click: x()"></div>')
    assert not template_rule_violations('<div hx-post="/x" hx-target="#y"></div>')


async def test_upload_adds_the_file_to_the_table(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": (FILE_NAME, b"hello", "text/plain")},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 200
    trigger = json.loads(response.headers["HX-Trigger"])
    assert "refreshUploadTable" in trigger
    assert trigger["showAlert"]["source"] == "upload-page"
    assert len(fake_minio.objects) == 1
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]
    table = await client.get("/get_uploaded_files", headers=HX)
    assert FILE_NAME in table.text


async def test_upload_needs_the_csrf_token(
    client, logged_in, db_session, stored_user, fake_minio
):
    response = await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": (FILE_NAME, b"hello", "text/plain")},
        headers=HX,
    )
    assert "Missing Cookie: `fastapi-csrf-token`" in response.text
    assert "<nav" not in response.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_a_file_that_fails_validation_is_not_stored(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": ("ab", b"hello", "text/plain")},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers
    assert 'id="error-message"' in response.text
    assert "<nav" not in response.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_upload_is_refused_for_a_regular_user(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": (FILE_NAME, b"hello", "text/plain")},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "Not authorized" in response.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_delete_needs_the_csrf_token(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    response = await client.delete(f"/delete/{row.unique_name}", headers=HX)
    assert "HX-Trigger" not in response.headers
    assert "Missing Cookie: `fastapi-csrf-token`" in response.text
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]


async def test_delete_removes_the_file_and_names_the_database_row(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    fake_minio.objects[row.unique_name] = b"hello"
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete/{row.unique_name}",
        params={"file_id": str(uuid.uuid4()), "group_name": "Spoofed"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert response.status_code == 200
    trigger = json.loads(response.headers["HX-Trigger"])
    assert trigger["showAlert"]["message"] == f"{FILE_NAME} deleted successfully."
    assert "refreshUploadTable" in trigger
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_delete_of_an_unknown_file_is_an_error_message(
    client, logged_in, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await client.delete(
        "/delete/unknown.txt", headers={**HX, "X-CSRF-Token": token}
    )
    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers
    assert "File not found" in response.text


async def test_delete_is_refused_for_a_regular_user(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    token = await csrf_token_from(client)
    logged_in.is_superuser = False
    response = await client.delete(
        f"/delete/{row.unique_name}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "Not authorized" in response.text
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]


async def test_a_file_name_with_quotes_and_script_stays_escaped(
    client, logged_in, db_session, stored_user, fake_minio
):
    await make_file(db_session, stored_user, name=NASTY_NAME)
    listing = await client.get("/get_uploaded_files", headers=HX)
    assert "<script" not in listing.text
    assert NASTY_NAME not in listing.text
    assert "&lt;script&gt;" in listing.text
    page = await client.get("/uploads", headers=HX)
    assert "<script" not in page.text
    for value in re.findall(r'hx-(?:get|delete)="([^"]*)"', page.text):
        assert "<" not in html.unescape(value)


async def test_an_uploaded_name_with_script_is_cleaned_and_escaped(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": (NASTY_NAME.replace('"', ""), b"hello", "text/plain")},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "refreshUploadTable" in response.headers["HX-Trigger"]
    listing = await client.get("/get_uploaded_files", headers=HX)
    assert "<script" not in listing.text


async def test_the_extension_cannot_carry_a_path_into_the_object_name(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": ('pytest-name.t/../x"y', b"hello", "text/plain")},
        headers={**HX, "X-CSRF-Token": token},
    )
    (object_name,) = fake_minio.objects
    assert re.fullmatch(r"[0-9a-f-]{36}\.[A-Za-z0-9]*", object_name)


async def test_an_anonymous_request_does_not_get_the_page(client, db_session):
    app.dependency_overrides.pop(current_active_user, None)
    response = await client.get("/uploads")
    assert response.status_code in (307, 401, 403)
    assert "<aside" not in response.text


def multipart(file_name=FILE_NAME, content=b"hello"):
    """A multipart body as bytes, plus its Content-Type header."""
    boundary = "pytestboundary"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="source"\r\n\r\n'
            f"upload-page\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, f"multipart/form-data; boundary={boundary}"


async def post_file(client, token, content=b"hello", name=FILE_NAME, headers=None):
    return await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": (name, content, "text/plain")},
        headers={**HX, "X-CSRF-Token": token, **(headers or {})},
    )


async def test_a_database_failure_removes_the_object_and_leaves_no_row(
    client, logged_in, db_session, stored_user, fake_minio, monkeypatch
):
    async def boom(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(upload_routes.upload_crud, "create", boom)
    token = await csrf_token_from(client)
    response = await post_file(client, token)
    assert "HX-Trigger" not in response.headers
    assert 'id="error-message"' in response.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_a_storage_error_string_is_an_error_and_writes_no_row(
    client, logged_in, db_session, stored_user, fake_minio
):
    fake_minio.fail_upload = True
    token = await csrf_token_from(client)
    response = await post_file(client, token)
    assert "HX-Trigger" not in response.headers
    assert STORAGE_UNAVAILABLE in response.text
    assert "Error occurred" not in response.text
    assert await stored_names(db_session, stored_user.id) == []


async def test_an_empty_and_an_oversize_file_are_refused_and_store_nothing(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    empty = await post_file(client, token, content=b"")
    assert "The file is empty" in empty.text
    big = await post_file(client, token, content=b"x" * 10_000_001)
    assert "greater than 10 MB" in big.text
    assert "HX-Trigger" not in empty.headers and "HX-Trigger" not in big.headers
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_a_file_of_exactly_the_limit_is_stored(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await post_file(client, token, content=b"x" * 10_000_000)
    assert "refreshUploadTable" in response.headers["HX-Trigger"]
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]


async def test_a_bad_content_length_is_refused_before_the_body_is_read(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    body, content_type = multipart()
    headers = {**HX, "X-CSRF-Token": token, "Content-Type": content_type}
    for length, text in (("99999999", "greater than 10 MB"), ("abc", "Content-Length")):
        response = await client.post(
            "/post_upload_file",
            content=body,
            headers={**headers, "Content-Length": length},
        )
        assert text in response.text
        assert "HX-Trigger" not in response.headers

    async def chunks():
        yield body

    # A chunked request has no Content-Length at all
    chunked = await client.post("/post_upload_file", content=chunks(), headers=headers)
    assert "Content-Length is required" in chunked.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []
    # The same body with an honest length is accepted
    ok = await client.post("/post_upload_file", content=body, headers=headers)
    assert "refreshUploadTable" in ok.headers["HX-Trigger"]


async def test_a_request_without_a_file_part_is_refused(
    client, logged_in, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await client.post(
        "/post_upload_file",
        data={"source": "upload-page", "file": "not an upload"},
        headers={**HX, "X-CSRF-Token": token},
    )
    assert "No file was uploaded" in response.text
    assert fake_minio.objects == {}


async def test_a_wrong_csrf_token_is_refused_on_upload_and_delete(
    client, logged_in, db_session, stored_user, fake_minio
):
    await csrf_token_from(client)  # sets a valid cookie; the header below is wrong
    wrong = {**HX, "X-CSRF-Token": "not-the-token"}
    uploaded = await client.post(
        "/post_upload_file",
        data={"source": "upload-page"},
        files={"file": (FILE_NAME, b"hello", "text/plain")},
        headers=wrong,
    )
    assert "HX-Trigger" not in uploaded.headers
    assert "CSRF" in uploaded.text
    assert fake_minio.objects == {}
    row = await make_file(db_session, stored_user)
    fake_minio.objects[row.unique_name] = b"hello"
    deleted = await client.delete(f"/delete/{row.unique_name}", headers=wrong)
    assert "HX-Trigger" not in deleted.headers
    assert "CSRF" in deleted.text
    assert row.unique_name in fake_minio.objects
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]


async def test_user_a_cannot_delete_or_download_user_bs_file(
    client, logged_in, db_session, stored_user, other_user, fake_minio
):
    row = await make_file(db_session, other_user)
    name = row.unique_name
    fake_minio.objects[name] = b"secret"
    token = await csrf_token_from(client)
    deleted = await client.delete(
        f"/delete/{name}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "File not found" in deleted.text
    assert "HX-Trigger" not in deleted.headers
    downloaded = await client.get(f"/download/{name}")
    assert "File not found" in downloaded.text
    assert b"secret" not in downloaded.content
    unknown = await client.get("/download/unknown.txt")
    assert "File not found" in unknown.text
    assert fake_minio.objects == {name: b"secret"}
    assert await stored_names(db_session, other_user.id) == [FILE_NAME]


async def test_the_streamed_download_has_the_security_headers(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    fake_minio.objects[row.unique_name] = b"mine"
    downloaded = await client.get(f"/download/{row.unique_name}")
    assert downloaded.content == b"mine"
    for name, value in SECURITY_HEADERS.items():
        assert downloaded.headers[name] == value


async def test_user_a_can_download_and_delete_their_own_file(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    name = row.unique_name
    fake_minio.objects[name] = b"mine"
    downloaded = await client.get(f"/download/{name}")
    assert downloaded.status_code == 200
    assert downloaded.content == b"mine"
    assert FILE_NAME in downloaded.headers["content-disposition"]
    token = await csrf_token_from(client)
    deleted = await client.delete(
        f"/delete/{name}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "refreshUploadTable" in deleted.headers["HX-Trigger"]
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_a_storage_error_on_delete_keeps_the_row(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    fake_minio.objects[row.unique_name] = b"hello"
    fake_minio.fail_remove = True
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete/{row.unique_name}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "HX-Trigger" not in response.headers
    assert STORAGE_UNAVAILABLE in response.text
    assert "Error occurred" not in response.text
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]


ODD_NAME = 'pytest-q"uote\nline é日本.txt'


async def test_an_odd_file_name_gives_a_valid_alert_header_and_download_header(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user, name=ODD_NAME)
    name = row.unique_name
    fake_minio.objects[name] = b"hello"
    downloaded = await client.get(f"/download/{name}")
    assert downloaded.status_code == 200
    disposition = downloaded.headers["content-disposition"]
    disposition.encode("ascii")
    assert "\n" not in disposition and "\r" not in disposition
    assert "filename*=UTF-8''" in disposition
    assert 'filename="pytest-q_uote_line' in disposition
    assert downloaded.content == b"hello"
    token = await csrf_token_from(client)
    deleted = await client.delete(
        f"/delete/{name}", headers={**HX, "X-CSRF-Token": token}
    )
    alert = json.loads(deleted.headers["HX-Trigger"])["showAlert"]
    assert alert["message"] == f"{ODD_NAME} deleted successfully."


async def test_an_upper_cased_unique_name_removes_the_right_object(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    name = row.unique_name
    fake_minio.objects[name] = b"hello"
    token = await csrf_token_from(client)
    response = await client.delete(
        f"/delete/{name.upper()}", headers={**HX, "X-CSRF-Token": token}
    )
    assert "refreshUploadTable" in response.headers["HX-Trigger"]
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_the_files_table_links_the_download_route(
    client, logged_in, db_session, stored_user
):
    row = await make_file(db_session, stored_user)
    listing = await client.get("/get_uploaded_files", headers=HX)
    assert re.search(rf'href="[^"]*/download/{row.unique_name}"', listing.text)
    assert "data-download" not in listing.text
    # The route sends Content-Disposition: attachment; a download attribute would
    # save a failed download's error page as the file
    assert not re.search(r"<a\b[^>]*\sdownload\b", listing.text)


async def test_a_transfer_encoding_header_is_refused_even_with_a_small_length(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    body, content_type = multipart()
    response = await client.post(
        "/post_upload_file",
        content=body,
        headers={
            **HX,
            "X-CSRF-Token": token,
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Transfer-Encoding": "chunked",
        },
    )
    assert "Content-Length is required" in response.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


def test_the_length_check_refuses_transfer_encoding_in_an_asgi_scope():
    def request(headers):
        scope = {"type": "http", "method": "POST", "headers": headers}
        return Request(scope)

    both = [(b"content-length", b"10"), (b"transfer-encoding", b"chunked")]
    with pytest.raises(HTTPException) as refused:
        upload_routes.check_content_length(request(both))
    assert refused.value.status_code == 411
    upload_routes.check_content_length(request([(b"content-length", b"10")]))


@pytest.fixture
def real_user_logged_in(stored_user):
    """The signed-in user as a real row loaded through the route's own session,
    so a rollback in the route expires it (a plain fake object cannot be)."""
    user_id = stored_user.id

    async def load_user(session: AsyncSession = Depends(get_async_session)):
        return await session.get(User, user_id)

    app.dependency_overrides[current_active_user] = load_user
    yield
    app.dependency_overrides.pop(current_active_user, None)


async def test_a_delete_error_with_a_real_user_row_is_not_a_500(
    client, real_user_logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    missing = await client.delete(
        "/delete/does-not-exist.txt", headers={**HX, "X-CSRF-Token": token}
    )
    assert missing.status_code == 200
    assert "File not found" in missing.text
    no_token = await client.delete("/delete/does-not-exist.txt", headers=HX)
    assert no_token.status_code == 200
    assert "X-CSRF-Token" in no_token.text


async def test_a_failed_database_create_with_a_real_user_row_is_not_a_500(
    client, real_user_logged_in, db_session, stored_user, fake_minio, monkeypatch
):
    async def boom(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(upload_routes.upload_crud, "create", boom)
    token = await csrf_token_from(client)
    response = await post_file(client, token)
    assert response.status_code == 200
    assert 'id="error-message"' in response.text
    assert fake_minio.objects == {}
    assert await stored_names(db_session, stored_user.id) == []


async def test_the_real_user_row_can_upload_and_list(
    client, real_user_logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    response = await post_file(client, token)
    assert "refreshUploadTable" in response.headers["HX-Trigger"]
    table = await client.get("/get_uploaded_files", headers=HX)
    assert FILE_NAME in table.text


STORAGE_HOST_ERROR = ConnectionError(
    "HTTPConnectionPool(host='minio.invalid', port=19999): Max retries exceeded "
    "with url: /throwaway-bucket?location="
)


def assert_storage_unavailable(response):
    assert response.status_code == 200
    assert STORAGE_UNAVAILABLE in response.text
    for detail in ("minio.invalid", "19999", "throwaway-bucket", "Max retries"):
        assert detail not in response.text


async def test_storage_connection_errors_show_only_the_fixed_message(
    client, logged_in, db_session, stored_user, fake_minio
):
    row = await make_file(db_session, stored_user)
    token = await csrf_token_from(client)
    fake_minio.raise_error = STORAGE_HOST_ERROR

    uploaded = await post_file(client, token)
    assert_storage_unavailable(uploaded)
    assert "HX-Trigger" not in uploaded.headers
    downloaded = await client.get(f"/download/{row.unique_name}")
    assert_storage_unavailable(downloaded)
    deleted = await client.delete(
        f"/delete/{row.unique_name}", headers={**HX, "X-CSRF-Token": token}
    )
    assert_storage_unavailable(deleted)
    assert "HX-Trigger" not in deleted.headers
    # The upload wrote no row and the delete removed none
    assert await stored_names(db_session, stored_user.id) == [FILE_NAME]


async def test_the_storage_detail_goes_to_the_log(
    client, logged_in, db_session, stored_user, fake_minio
):
    token = await csrf_token_from(client)
    fake_minio.raise_error = STORAGE_HOST_ERROR
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="ERROR")
    try:
        await post_file(client, token)
    finally:
        logger.remove(sink)
    assert any("minio.invalid" in line for line in lines)
