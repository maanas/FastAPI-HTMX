---
id: 2026-10-14-htmx-patterns-error-answers
status: proposed
target: skills/htmx-patterns/reference/responses.md
metric: correctness
---
Evidence: log 2026-10-14, task "htmx leftovers", steps 2, 3a, 3b, 4: coder and reviewer reported these skill lines as stale (the skills still describe the pre-task design); skills change only through a proposal. Covers responses.md, security.md, SKILL.md, flowbite-alpine.md and testing.md of htmx-patterns. Related applied: 2026-10-13-security-reference-update.
Change:
```diff
--- a/skills/htmx-patterns/reference/responses.md
+++ b/skills/htmx-patterns/reference/responses.md
-htmx 2 swaps 2xx responses only; 4xx and 5xx are not swapped.
+htmx 2 swaps 2xx only. `handle_error` (`app/routes/view/errors.py`) sets `X-Error-Rendered` on a form or view error answer and the `htmx:beforeSwap` listener in `app/static/js/shell.js` lets exactly those swap.
-| Form is invalid | ... `422` is allowed to swap through `responseHandling` in the `htmx-config` meta tag. Never `200` for an invalid form. |
+| Form is invalid | The form partial with the messages and typed values (`form` from `submitted_form`), status `422`, marker header set. Never `200` for an invalid form. |
-| Not allowed, missing | `403` / `404`, no swap, a toast through `HX-Trigger` |
+| Not allowed, missing | Form and view errors swap with their status. A delete in a list uses `alert_error` (`showAlert`), no swap. An unknown path swaps the not-found fragment only for `HX-Target: dashboard-body`. |
@@ ## Redirects
+`http_exception_handler` in `app/exception.py` keeps status and detail; a 401 answers `HX-Redirect`.
--- a/skills/htmx-patterns/reference/security.md
+++ b/skills/htmx-patterns/reference/security.md
-- The page route (`GET`) creates the pair with `csrf_protect.generate_csrf_tokens()`, sets the signed
-  cookie with `csrf_protect.set_csrf_cookie(signed_token, response)` and passes `csrf_token` to the
-  template. `app/routes/view/role.py` shows it.
+- The page route (`GET`) calls `csrf_token_for(request)` and `set_csrf_cookie(...)` from
+  `app/routes/view/csrf.py` (reuses a valid cookie, no rotation after a write; login issues a new pair).
-  `<body>`, not repeated on each form. A partial route reads it back from the request header when it
-  needs to re-render a form.
+  `<body>`, not repeated on each form. A partial route that re-renders a form uses `csrf_token_for` too.
-- `responseHandling` is added here when `422` must swap (see `responses.md`).
+- `responseHandling` is not used; swapping of errors is the `X-Error-Rendered` listener (`responses.md`).
--- a/skills/htmx-patterns/SKILL.md
+++ b/skills/htmx-patterns/SKILL.md
-- htmx 2 swaps 2xx only. An invalid form returns the form partial with `422`.
+- htmx 2 swaps 2xx only, plus error answers carrying `X-Error-Rendered`. An invalid form returns the form partial with `422`.
--- a/skills/htmx-patterns/reference/flowbite-alpine.md
+++ b/skills/htmx-patterns/reference/flowbite-alpine.md
-| `htmx:responseError` | One place to show a toast for 4xx and 5xx |
+| `htmx:responseError` | Error alerts come from the `showAlert` event, with no swap |
--- a/skills/htmx-patterns/reference/testing.md
+++ b/skills/htmx-patterns/reference/testing.md
-5. An invalid form: `422` and the message in the body.
+5. An invalid form: `422`, the `X-Error-Rendered` header and the message in the body; a fragment answer starts with `<title>` (`after_title` in `app/tests/error_asserts.py`).
```
Why: the next worker reads the shipped error design instead of the pre-task one. (Testing.md stays under 60 lines; responses.md grows by about 3.)
