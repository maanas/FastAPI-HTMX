---
id: 2026-10-13-route-guard-existing-callers
status: applied
applied: 2026-10-13
target: skills/htmx-patterns/reference/security.md
note: applied to the CSRF section of security.md instead of skills/new-page/reference/route.md, which would have gone from 59 to 62 lines (reference files stay under 60)
metric: correctness
---
Evidence: log 2026-10-13, "Security" step 2: a CSRF dependency put on the whole auth router broke logout, because `shell.js` posts without a token; the suite stayed green (test_shell checks markup only). Found by the reviewer and independently by the checker's smoke. Related to the applied route-error-path-checklist, which covers handlers but not router-wide dependencies.
Change:
```diff
--- a/skills/new-page/reference/route.md
+++ b/skills/new-page/reference/route.md
@@ -49,0 +50,3 @@
+- A dependency or middleware on a whole router changes every route under it. Grep the templates and
+  `app/static/js/` for each existing caller (forms, `fetch`, `hx-post`) and test one real request per
+  caller, not only the markup.
```
Why: one grep and one request per caller catches a guard that locks out an existing client.
