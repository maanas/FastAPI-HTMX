# Responses

## Partial or page

- A request with `HX-Request: true` gets a partial from `app/templates/partials/`; a normal request
  gets a page from `app/templates/pages/` that extends the base shell.
- One URL can serve both: branch on `request.headers.get("HX-Request")`.
- A boosted or history-restore request (`HX-Boosted`, `HX-History-Restore-Request`) needs the full
  page even though `HX-Request` is set.
- A partial is a fragment: no `<html>`, no `<head>`, no base template. Its root element carries the
  `id` that the trigger's `hx-target` names.
- Send `Vary: HX-Request` when one URL returns both, so a cache never serves a partial as a page.

## Status codes

htmx 2 swaps 2xx only. `handle_error` (`app/routes/view/errors.py`) sets `X-Error-Rendered` on a
form or view error answer and the `htmx:beforeSwap` listener in `app/static/js/shell.js` lets
exactly those swap.

| Case | Response |
|---|---|
| Form is invalid | The form partial with the messages and typed values (`form` from `submitted_form`), status `422`, marker header set. Never `200` for an invalid form. |
| Created, updated | The updated row or list partial, `200` |
| Deleted | `200` with an empty body and `hx-swap="outerHTML"` on the row, or `204` with an `HX-Trigger` |
| Not allowed, missing | Form and view errors swap with their status. A delete in a list uses `alert_error` (`showAlert`), no swap. An unknown path swaps the not-found fragment only for `HX-Target: dashboard-body`. |
| Signed out | `HX-Redirect: /login`, see below |

## Response headers

| Header | Use |
|---|---|
| `HX-Trigger` | Fire a client event with JSON detail. `{"showAlert": {...}}` is what `app/static/js/components.js` listens for. |
| `HX-Redirect` | Full navigation (after login, after logout, when signed out) |
| `HX-Location` | Navigation without a full reload |
| `HX-Retarget`, `HX-Reswap` | Send an error partial somewhere other than the trigger's target |
| `HX-Push-Url` | Put the canonical URL in the address bar after a swap |
| `HX-Refresh` | Reload the page |

Build an `HX-Trigger` value with `json.dumps`, never by string concatenation.

## Redirects

htmx follows a `3xx` silently and swaps the result into the target, so a signed-out user would see
the login page inside a table. An auth dependency or handler that redirects must check `HX-Request`
and answer `200` (or `401`) with `HX-Redirect` instead.
`http_exception_handler` in `app/exception.py` keeps status and detail; a 401 answers `HX-Redirect`.

## Errors

Route errors go through `handle_error` in `app/routes/view/errors.py`, as `app/routes/view/role.py`
does. Do not add a second error path.
