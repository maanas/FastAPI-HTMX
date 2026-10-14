import json
import traceback
from typing import Dict, Optional, Union

from fastapi.responses import HTMLResponse
from fastapi_csrf_protect.exceptions import CsrfProtectError
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.routes.view.fragments import render_view
from app.templates import templates

# htmx swaps 2xx only. An error answer rendered here carries this header, and the
# htmx:beforeSwap listener in app/static/js/shell.js swaps only such answers: an
# unhandled 500, the JSON 403 of csrf_error_handler or a proxy page never replace
# content.
ERROR_RENDERED_HEADER = "X-Error-Rendered"
# All the user sees of a failed CSRF check or a crash: the exception goes to the log
CSRF_MESSAGE = "Your session has expired. Reload the page and try again."
UNEXPECTED_MESSAGE = "Something went wrong. Please try again."
INVALID_MESSAGE = "The submitted data is not valid."


def validation_message(err: dict) -> str:
    """One readable line for a pydantic error: the field, then the message."""
    field = ".".join(str(part) for part in err["loc"])
    message = str(err["msg"]).removeprefix("Value error, ")
    return f"{field}: {message}" if field else message


def describe_exception(error: BaseException) -> str:
    """The type of `error`, and its message unless it is a database error.

    A SQLAlchemy message carries the statement and its parameters (user data), so
    for those only the type and the type of the wrapped driver error are given.
    """
    name = type(error).__name__
    if isinstance(error, SQLAlchemyError):
        orig = getattr(error, "orig", None)
        return f"{name} (driver: {type(orig).__name__})" if orig else name
    return f"{name}: {error}"


def log_unexpected(error: BaseException) -> None:
    """Log an unhandled error: the chain with types and frames, never variable values.

    The exception object is not passed to loguru: its default sink prints the local
    variables of every frame (form values, emails, tokens). The frames come from the
    standard library, which gives file, line, function and source line only.
    """
    lines = []
    seen = set()
    pending = [error]
    while pending:
        current = pending.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        frames = "".join(traceback.format_tb(current.__traceback__))
        lines.append(f"{describe_exception(current)}\n{frames}")
        pending.extend(
            e for e in (current.__cause__, current.__context__) if e is not None
        )
    # A plain string: loguru does not format a message that has no arguments
    logger.error("Unhandled error in a view route\n" + "\n".join(lines))


def error_status_and_messages(
    error: Union[ValidationError, HTTPException, Exception],
) -> tuple[int, list[str]]:
    """The status and the user-visible messages for `error`.

    Only a message the app wrote itself reaches the user: a field message of a
    schema, an HTTPException detail, or a fixed text. Any other exception is
    logged with its traceback and shown as a fixed message.
    """
    if isinstance(error, ValidationError):
        return 422, [validation_message(err) for err in error.errors()] or [
            INVALID_MESSAGE
        ]
    if isinstance(error, HTTPException):
        if isinstance(error.detail, str) and error.detail:
            return error.status_code, [error.detail]
        return error.status_code, [UNEXPECTED_MESSAGE]
    if isinstance(error, CsrfProtectError):
        logger.warning("CSRF check failed in a view route")
        return 403, [CSRF_MESSAGE]
    log_unexpected(error)
    return 500, [UNEXPECTED_MESSAGE]


def handle_error(
    template: str,
    context: Dict,
    error: Union[ValidationError, HTTPException, Exception],
    fragment: Optional[str] = None,
) -> templates.TemplateResponse:
    """
    Handles errors that occur during the processing of a request, and returns a template
    response with the appropriate error messages and status.

    Status: ValidationError 422, HTTPException its own status_code, a failed CSRF
    check 403, anything else 500.

    Args:
        template (str): The name of the template to render.
        context (dict): This is a dictionary containing the data that will be passed to the template.
        It should include the request object and any database objects that need to be rendered in the template.
        For example, you might pass {"request": request, "group": await group_crud.read_by_primary_key(db, group_id)} as the context.
        error (Exception): This is the exception that was raised during the execution of your code.
        fragment (str, optional): The fragment for `template` (a page). An HTMX request
        gets the fragment, any other request gets `template`: no shell nested in a swap.

    Returns:
        A FastAPI response containing the rendered template with the error messages.
    """
    status, error_messages = error_status_and_messages(error)
    # Key names only: the values hold user emails and the CSRF token
    logger.info(
        f"context keys: {sorted(context)}, error: {type(error).__name__}, "
        f"status: {status}"
    )

    context["error_messages"] = error_messages
    if fragment:
        response = render_view(
            context["request"], template, fragment, context, status_code=status
        )
    else:
        response = templates.TemplateResponse(
            context["request"], template, context, status_code=status
        )
    response.headers[ERROR_RENDERED_HEADER] = "1"
    return response


def alert_error(
    error: Union[ValidationError, HTTPException, Exception], source: str
) -> HTMLResponse:
    """The answer to a refused or failed action inside a list (a delete).

    The list stays as it is: no body, `HX-Reswap: none`, and a `showAlert` event of
    type `error` that the `listAlerts` / `uploadPage` component (the element with
    id `source`) displays. htmx reads `HX-Trigger` on any status.
    """
    status, error_messages = error_status_and_messages(error)
    logger.info(f"alert for #{source}, error: {type(error).__name__}, status: {status}")
    headers = {
        "HX-Reswap": "none",
        "HX-Trigger": json.dumps(
            {
                "showAlert": {
                    "type": "error",
                    "message": " ".join(error_messages),
                    "source": source,
                }
            }
        ),
    }
    return HTMLResponse(content="", status_code=status, headers=headers)
