import json
import re
import uuid
from urllib.parse import quote

import nh3
from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.routing import APIRouter
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.minio_core import minio
from app.database.db import CurrentAsyncSession
from app.database.security import current_active_user
from app.models.upload import Upload as UploadsModelDB
from app.models.users import User as UserModelDB
from app.routes.view.csrf import csrf_token_for, set_csrf_cookie
from app.routes.view.errors import handle_error
from app.routes.view.fragments import render_view
from app.routes.view.view_crud import SQLAlchemyCRUD
from app.schema.uploads import FileCreate
from app.templates import templates

upload_crud = SQLAlchemyCRUD[UploadsModelDB](UploadsModelDB)
upload_view_route = APIRouter()

# Fragments (no layout) and the page that includes the first, see fragments.py
UPLOAD_PAGE = "partials/upload/upload.html"
UPLOAD_FILES = "partials/upload/files_table.html"
# The error of an upload or a delete, swapped into #upload-result
UPLOAD_RESULT = "partials/upload/upload_result.html"
# What MinioClient returns instead of raising
MINIO_ERROR = "Error occurred:"
# All the user sees of a storage failure: the detail (host, bucket) goes to the log
STORAGE_UNAVAILABLE = "File storage is not available. Try again later."
MAX_FILE_SIZE = 10_000_000
# The limit plus room for the multipart envelope (boundaries and part headers)
MAX_BODY_SIZE = MAX_FILE_SIZE + 64 * 1024


def check_content_length(request: Request) -> None:
    """Refuse a body of unknown or too large size before it is read."""
    # A chunked body is unbounded whatever Content-Length says
    if "Transfer-Encoding" in request.headers:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    try:
        length = int(request.headers.get("Content-Length", ""))
    except ValueError:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    if length < 0 or length > MAX_BODY_SIZE:
        raise HTTPException(
            status_code=413, detail="File size cannot be greater than 10 MB"
        )


async def storage(action: str, call, *args):
    """Run a storage call; an exception or an "Error occurred" string is logged
    and becomes the fixed message."""
    try:
        result = await call(*args)
    except Exception as err:
        logger.error(f"{action}: storage failed: {type(err).__name__}: {err}")
        raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE)
    if isinstance(result, str) and result.startswith(MINIO_ERROR):
        logger.error(f"{action}: storage failed: {result}")
        raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE)
    return result


async def rollback(db: CurrentAsyncSession, action: str) -> None:
    try:
        await db.rollback()
    except Exception as err:
        logger.error(f"{action}: rollback failed: {type(err).__name__}")


async def remove_object(unique_name: str, action: str) -> bool:
    """Remove a stored object; the client returns an error string, it does not raise."""
    try:
        result = await minio.remove_file(unique_name)
    except Exception as err:
        logger.error(f"{action}: removing {unique_name} failed: {type(err).__name__}")
        return False
    if result.startswith(MINIO_ERROR):
        logger.error(f"{action}: removing {unique_name} failed: {result}")
        return False
    return True


async def read_owned_file(
    db: CurrentAsyncSession, user_id: uuid.UUID, unique_name: str
):
    """The user's own file row; a missing and a foreign file answer the same."""
    rows = await upload_crud.read_by_column(db, "unique_name", unique_name)
    if rows is None:
        rows = []
    owned = [
        r for r in (rows if isinstance(rows, list) else [rows]) if r.user_id == user_id
    ]
    if not owned:
        raise HTTPException(status_code=404, detail="File not found")
    return owned[0]


def content_disposition(name: str) -> str:
    """An attachment header that quotes, newlines or non-ASCII cannot break."""
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    return (
        f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"
    )


async def read_files(
    db: CurrentAsyncSession, user_id: uuid.UUID, skip: int, limit: int
):
    """The files of `user` as a list; `read_by_column` gives None, a row or a list."""
    files = await upload_crud.read_by_column(db, "user_id", user_id, skip, limit)
    if files is None:
        return []
    return files if isinstance(files, list) else [files]


@upload_view_route.get("/uploads", response_class=HTMLResponse)
async def get_upload_file(
    request: Request,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    skip: int = 0,
    limit: int = 100,
    csrf_protect: CsrfProtect = Depends(),
):
    # Read once: a rollback expires the user object, and reading it afterwards fails
    is_superuser = current_user.is_superuser
    user_id = current_user.id
    try:
        if not is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to upload files"
            )
        files = await read_files(db, user_id, skip, limit)
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = render_view(
            request,
            "pages/upload.html",
            UPLOAD_PAGE,
            {
                "request": request,
                "files": files,
                "user_type": is_superuser,
                "csrf_token": csrf_token,
            },
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response
    except Exception as e:
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/upload.html",
            {
                "request": request,
                "user_type": is_superuser,
                "csrf_token": csrf_token,
            },
            e,
            fragment=UPLOAD_PAGE,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


@upload_view_route.post("/post_upload_file", response_class=HTMLResponse)
async def post_upload_file(
    request: Request,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    # The body is not parsed (no UploadFile parameter) until the checks have passed
    # Read once: a rollback expires the user object, and reading it afterwards fails
    is_superuser = current_user.is_superuser
    user_id = current_user.id
    stored = None
    try:
        check_content_length(request)
        await csrf_protect.validate_csrf(request)

        if not is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to upload files"
            )

        form = await request.form()
        # Release the spooled upload on every path; nothing reads it after this
        try:
            file = form.get("file")
            if not isinstance(file, StarletteUploadFile):
                raise HTTPException(status_code=400, detail="No file was uploaded")
            if not file.filename:
                raise HTTPException(status_code=400, detail="Filename is missing")
            # FileBase.validate_file_size intends this limit but the shared schema code
            # drops it, so it is enforced here, before anything is stored
            if not file.size:
                raise HTTPException(status_code=400, detail="The file is empty")
            if file.size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, detail="File size cannot be greater than 10 MB"
                )
            # The extension becomes part of the object name and of a URL: letters and
            # digits only, and short enough for the unique_name column
            file_extension = re.sub(r"[^A-Za-z0-9]", "", file.filename.split(".")[-1])[
                :10
            ]
            unique_name = f"{uuid.uuid4()}.{file_extension}"

            # Validate (type, name) before anything is stored
            file_create = FileCreate(
                name=nh3.clean(str(file.filename)),
                unique_name=unique_name,
                file_type=nh3.clean(str(file.content_type)),
                source=nh3.clean(str(form.get("source"))),
                file_size=file.size,
                user_id=user_id,
            )

            file_url = await storage("upload", minio.upload_file, file, unique_name)
            stored = unique_name

            await upload_crud.create(dict(file_create), db)
            # The row is committed: a later failure must not remove the object
            stored = None

            headers = {
                "HX-Trigger": json.dumps(
                    {
                        "showAlert": {
                            "type": "added",
                            "message": (
                                f"{file_create.name} uploaded successfully. "
                                f"URL: {file_url}"
                            ),
                            "source": "upload-page",
                        },
                        "refreshUploadTable": "",
                    }
                ),
            }
            return HTMLResponse(content="", headers=headers)
        finally:
            await form.close()
    except Exception as e:
        # A failed write leaves the session unusable, and the stored object has no
        # row: undo both. Nothing ran for a request that failed an earlier check.
        if stored:
            await rollback(db, "upload")
            await remove_object(stored, "upload")
        return handle_error(
            UPLOAD_RESULT,
            {"request": request, "user_type": is_superuser},
            e,
        )


# Making a route to get the uploaded files
# Its fragment fills the table body, not the content area, so every request gets
# the fragment and there is no page for it
@upload_view_route.get("/get_uploaded_files", response_class=HTMLResponse)
async def get_uploaded_files(
    request: Request,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    skip: int = 0,
    limit: int = 100,
):
    # Read once: a rollback expires the user object, and reading it afterwards fails
    is_superuser = current_user.is_superuser
    user_id = current_user.id
    try:
        if not is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized to view files")
        files = await read_files(db, user_id, skip, limit)
        return templates.TemplateResponse(
            request,
            UPLOAD_FILES,
            {
                "request": request,
                "files": files,
                "user_type": is_superuser,
            },
        )
    except Exception as e:
        return handle_error(
            UPLOAD_FILES,
            {
                "request": request,
                "user_type": is_superuser,
            },
            e,
        )


# Route to download a file from the back end
@upload_view_route.get("/download/{file_unique_name}")
async def download_file(
    request: Request,
    file_unique_name: str,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    # Read once: a rollback expires the user object, and reading it afterwards fails
    is_superuser = current_user.is_superuser
    user_id = current_user.id
    try:
        if not is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to download files"
            )

        # Before the storage is asked for anything
        row = await read_owned_file(db, user_id, file_unique_name)

        file_response = await storage("download", minio.get_file, row.unique_name)
        return StreamingResponse(
            file_response,
            media_type="application/octet-stream",
            headers={"Content-Disposition": content_disposition(row.name)},
        )
    except Exception as e:
        csrf_token, signed_token = csrf_token_for(request, csrf_protect)
        response = handle_error(
            "pages/upload.html",
            {"request": request, "user_type": is_superuser, "csrf_token": csrf_token},
            e,
            fragment=UPLOAD_PAGE,
        )
        set_csrf_cookie(csrf_protect, response, signed_token)
        return response


# Route to delete a file from the back end
@upload_view_route.delete("/delete/{file_unique_name}")
async def delete_file(
    request: Request,
    file_unique_name: str,
    db: CurrentAsyncSession,
    current_user: UserModelDB = Depends(current_active_user),
    csrf_protect: CsrfProtect = Depends(),
):
    # Read once: a rollback expires the user object, and reading it afterwards fails
    is_superuser = current_user.is_superuser
    user_id = current_user.id
    try:
        await csrf_protect.validate_csrf(request)

        if not is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete files"
            )

        # Found by its unique name and owner; the name for the alert comes from the
        # row, and so does the object name (the lookup ignores case, object names
        # do not)
        row = await read_owned_file(db, user_id, file_unique_name)
        file_id, file_name, object_name = row.id, row.name, row.unique_name

        await storage("delete", minio.remove_file, object_name)
        await upload_crud.delete(db, file_id)
        headers = {
            "HX-Trigger": json.dumps(
                {
                    "showAlert": {
                        "type": "deleted",
                        "message": f"{file_name} deleted successfully.",
                        "source": "upload-page",
                    },
                    "refreshUploadTable": "",
                }
            ),
        }
        return HTMLResponse(content="", headers=headers)
    except Exception as e:
        # A failed delete leaves the session unusable; the error response reads no data
        await rollback(db, "delete")
        return handle_error(
            UPLOAD_RESULT,
            {"request": request, "user_type": is_superuser},
            e,
        )
