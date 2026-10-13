---
id: 2026-10-13-security-reference-update
status: applied
applied: 2026-10-13
target: skills/htmx-patterns/reference/security.md
metric: correctness
---
Evidence: log 2026-10-13, "Security" step 3: reviewer noted `allowScriptTags: false` was missing against this file (applied by the director); coder and reviewer could not edit the skill. The file does not list the shipped policy and headers, HSTS following COOKIE_SECURE, the API docs pages being off, or that the template guard now covers `hx-headers` with `js:` and `hx-trigger` filters. Also open from "Alpine CSP build": flowbite-alpine.md states the Alpine CSP rule more strictly than 3.17.4 (separate fix, not in this diff).
Change:
```diff
--- a/skills/htmx-patterns/reference/security.md
+++ b/skills/htmx-patterns/reference/security.md
@@ -22,2 +22,9 @@
 - any script, stylesheet, font or image from another origin (no CDN)
+- `hx-headers` or `hx-vals` with `js:`, and `hx-trigger` filters (both need `eval`); the guard in
+  `app/tests/template_rules.py` rejects them
+
+`app/core/security_headers.py` (pure ASGI middleware) sends the policy and `X-Content-Type-Options`,
+`Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy` and `Cross-Origin-Opener-Policy` on every
+response. `Strict-Transport-Security` is sent only when `COOKIE_SECURE` is true. The API docs pages
+are off (Swagger UI needs a CDN and inline script). Change the policy in that file, not per route.
```
Why: the next worker reads one accurate page instead of rediscovering the shipped policy from code.
