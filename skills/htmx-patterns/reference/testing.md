# Testing a route that answers HTMX

Tests live in `app/tests/`, run with `.venv/bin/python -m pytest -q app/tests`.

For each route:

1. Without the header: status `200`, the body contains `<html`.
2. With `headers={"HX-Request": "true"}`: status `200`, the body has no `<html` and contains the
   root `id` the trigger targets.
3. Signed out, with the header: an `HX-Redirect` header, not a `3xx`.
4. A write without `X-CSRF-Token`: refused, nothing stored.
5. An invalid form: `422`, the `X-Error-Rendered` header and the message in the body; a fragment
   answer starts with `<title>` (`after_title` in `app/tests/error_asserts.py`).
6. Each `HX-*` header the route sets: assert its value (`json.loads` for `HX-Trigger`).

Use `httpx.AsyncClient` with `ASGITransport(app=app)` and override `current_active_user` and the
session dependency through `app.dependency_overrides`; do not sign in through the login route in
every test.

A route whose error path rolls back needs one test with a real user row loaded through the route's
own session (not the plain fake), that triggers the error and asserts the 4xx. A fake user cannot be
expired by the rollback and hides `MissingGreenlet`.
