---
name: htmx-patterns
description: HTMX 2 patterns for this FastAPI + Jinja2 starter - partial versus full responses, targets and swaps, CSRF, validation errors, response headers, Flowbite and Alpine after a swap, and what the strict content security policy forbids. Use when adding or changing an hx-* attribute, a route that answers an HTMX request, or JS that listens to htmx events.
---
# HTMX patterns

## Essentials

- `HX-Request: true` gets a partial from `templates/partials/`; a normal request gets a full page.
- Always name `hx-target`; the partial's root carries that `id`.
- htmx 2 swaps 2xx only, plus error answers carrying `X-Error-Rendered`. An invalid form returns
  the form partial with `422`.
- Every write route calls `csrf_protect.validate_csrf(request)` first; the token travels in
  `X-CSRF-Token`.
- No inline script, `on*=`, `hx-on:*` or `style=`: the content security policy blocks them.
- Markup swapped in needs Flowbite initialised again, by one shared listener.
- A redirect to an HTMX request is `HX-Redirect`, never a `3xx`.

## Contents

| Read | When |
|---|---|
| [reference/responses.md](reference/responses.md) | Writing a route: partial or page, status codes, `HX-*` response headers |
| [reference/attributes.md](reference/attributes.md) | Writing markup: targets, swaps, triggers, out-of-band, indicators |
| [reference/security.md](reference/security.md) | CSRF, the content security policy, the `htmx-config` meta tag, escaping |
| [reference/flowbite-alpine.md](reference/flowbite-alpine.md) | Flowbite or Alpine inside swapped content, or JS that listens to htmx events |
| [reference/testing.md](reference/testing.md) | Testing a route that answers HTMX |
| [reference/browser-pass.md](reference/browser-pass.md) | Checking a page or a swapped partial in a real browser |

htmx is 2.0.11, vendored at `app/static/vendor/htmx/htmx.min.js` (see `VENDORED.md`). The app's own
scripts stay in `app/static/js/`.
Official reference: https://htmx.org/reference/ and https://htmx.org/migration-guide-htmx-1/.
