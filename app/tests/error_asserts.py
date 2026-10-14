"""What a refused action inside a list answers, shared by the view tests."""

import json

from app.routes.view.errors import CSRF_MESSAGE, UNEXPECTED_MESSAGE  # noqa: F401


def alert_message(response):
    """Assert `response` is a no-swap alert answer and return the alert's message.

    The list stays as it is: an empty body, `HX-Reswap: none`, no `HX-Location`,
    and a `showAlert` trigger of type `error` for the component named by `source`.
    """
    assert 400 <= response.status_code < 600
    assert response.text == ""
    assert response.headers["HX-Reswap"] == "none"
    assert "HX-Location" not in response.headers
    # No marker: htmx must not swap this answer
    assert "X-Error-Rendered" not in response.headers
    alert = json.loads(response.headers["HX-Trigger"])["showAlert"]
    assert alert["type"] == "error"
    assert alert["source"].endswith("-page")
    return alert["message"]
