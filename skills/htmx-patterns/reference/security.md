# Security

## CSRF

- The page route (`GET`) calls `csrf_token_for(request, csrf_protect)` and `set_csrf_cookie(...)` from
  `app/routes/view/csrf.py` (reuses a valid cookie, no rotation after a write; login issues a new
  pair) and passes `csrf_token` to the template. `app/routes/view/role.py` shows it.
- Every `POST`, `PUT`, `PATCH` and `DELETE` handler starts with
  `await csrf_protect.validate_csrf(request)`, before any read of the form.
- The token travels in the `X-CSRF-Token` header, set once on the shell through `hx-headers` on
  `<body>`, not repeated on each form. A partial route that re-renders a form uses `csrf_token_for`
  too.
- A `fetch` call in `app/static/js/` sends the same header.
- A dependency or middleware on a whole router changes every route under it. Grep the templates and
  `app/static/js/` for each existing caller (forms, `fetch`, `hx-post`) and test one real request per
  caller, not only the markup.

## Content security policy

The policy is own origin only, no inline script. Not allowed in any template or partial:

- `<script>` with a body, `on*=` attributes, `javascript:` URLs
- `hx-on:*` attributes and `hx-vals='js:...'` (both need `eval`)
- inline `style=`
- any script, stylesheet, font or image from another origin (no CDN)
- `hx-headers` or `hx-vals` with `js:`, and `hx-trigger` filters (both need `eval`); the guard in
  `app/tests/template_rules.py` rejects them

`app/core/security_headers.py` (pure ASGI middleware) sends the policy and `X-Content-Type-Options`,
`Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy` and `Cross-Origin-Opener-Policy` on every
response. `Strict-Transport-Security` is sent only when `COOKIE_SECURE` is true. The API docs pages
are off (Swagger UI needs a CDN and inline script). Change the policy in that file, not per route.

## htmx config

One meta tag in the shell, nowhere else:

```html
<meta name="htmx-config" content='{"allowEval": false, "allowScriptTags": false, "includeIndicatorStyles": false, "selfRequestsOnly": true}'>
```

- `includeIndicatorStyles: false` stops htmx from injecting a `<style>` tag; the `.htmx-indicator`
  rules go in the stylesheet.
- `responseHandling` is not used; swapping of errors is the `X-Error-Rendered` listener (`responses.md`).

## Escaping

- Jinja autoescapes; keep it on. `|safe` only on HTML that went through `nh3.clean` on the server.
- Form values go through `nh3.clean` and then the Pydantic schema before they are stored.
- User text in an attribute is escaped by Jinja; user text in an `HX-Trigger` header is serialised
  with `json.dumps`.
- An `id` built from user data is not allowed; use the record's id.
