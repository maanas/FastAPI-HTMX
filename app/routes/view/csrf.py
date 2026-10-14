from datetime import datetime, timezone

from fastapi import Request, Response
from fastapi_csrf_protect import CsrfProtect
from itsdangerous import BadData, URLSafeTimedSerializer


def csrf_token_for(
    request: Request, csrf_protect: CsrfProtect
) -> tuple[str, str | None]:
    """The token to render, and the signed cookie value when a new pair was made.

    A cookie the request already carries is reused while it is valid and has more
    than half of its lifetime left: the signed value holds the token, so a second
    tab keeps the first tab's token working. Otherwise a new pair is generated and
    its signed value must go to the response (`set_csrf_cookie`).

    Signing and the lifetime come from the library's own settings, so what this
    returns passes `validate_csrf` together with the cookie.
    """
    signed = request.cookies.get(csrf_protect._cookie_key)
    if signed and csrf_protect._secret_key:
        serializer = URLSafeTimedSerializer(
            csrf_protect._secret_key, salt="fastapi-csrf-token"
        )
        try:
            token, issued = serializer.loads(
                signed, max_age=csrf_protect._max_age, return_timestamp=True
            )
        except BadData:  # tampered, malformed or expired
            pass
        else:
            age = (datetime.now(timezone.utc) - issued).total_seconds()
            if isinstance(token, str) and token and age < csrf_protect._max_age / 2:
                return token, None
    token, signed = csrf_protect.generate_csrf_tokens()
    return token, signed


def set_csrf_cookie(
    csrf_protect: CsrfProtect, response: Response, signed_token: str | None
) -> None:
    """Set the CSRF cookie when `csrf_token_for` made a new pair; else do nothing."""
    if signed_token:
        csrf_protect.set_csrf_cookie(signed_token, response)


def rotate_csrf_cookie(response: Response) -> None:
    """Replace the CSRF cookie on `response` with a new pair.

    The token is not tied to a user, so a cookie that existed before login (planted
    through a sibling subdomain or plain http) would stay valid after it. Login
    calls this so the signed-in session starts with a pair only the server made.
    """
    csrf_protect = CsrfProtect()
    _, signed = csrf_protect.generate_csrf_tokens()
    csrf_protect.set_csrf_cookie(signed, response)
