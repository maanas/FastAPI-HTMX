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

htmx 2 swaps 2xx responses only; 4xx and 5xx are not swapped.

| Case | Response |
|---|---|
| Form is invalid | The form partial with the messages, status `422`; `422` is allowed to swap through `responseHandling` in the `htmx-config` meta tag. Never `200` for an invalid form. |
| Created, updated | The updated row or list partial, `200` |
| Deleted | `200` with an empty body and `hx-swap="outerHTML"` on the row, or `204` with an `HX-Trigger` |
| Not allowed, missing | `403` / `404`, no swap, a toast through `HX-Trigger` |
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

## Errors

Route errors go through `handle_error` in `app/routes/view/errors.py`, as `app/routes/view/role.py`
does. Do not add a second error path.
