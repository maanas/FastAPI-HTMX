---
id: 2026-10-13-route-error-path-checklist
status: proposed
target: skills/new-page/reference/route.md
metric: correctness
---
Evidence: log 2026-10-13, task "Templates to Flowbite v4 markup": every page step found the same route defects. Step 3: unescaped token, no self-delete guard. Step 5: duplicate rename gave 500. Step 6: unknown user id gave 500, `handle_error` logged emails and the CSRF token. Step 7: model data read before auth and CSRF, no ownership check, and a delete error path answering 500 through `MissingGreenlet` because a rollback expired `current_user`; no test saw it because tests override `current_active_user` with a plain fake that a rollback cannot expire. Only the checker's request against a started app found it. The director carried the growing checklist into each coder prompt by hand.
Change:
```diff
--- a/skills/new-page/reference/route.md
+++ b/skills/new-page/reference/route.md
@@
 - No blocking call (file, network, `time.sleep`) in an async handler.
+- Order in a write handler: auth dependency, `validate_csrf`, superuser or ownership check, then read
+  the form and touch model data. Never read the body or a model row before these.
+- A unique violation or an unknown foreign key id is a 4xx alert (`IntegrityError` caught, rollback),
+  never a 500. Alert text is fixed server text, not client input, and never shows a host, bucket or
+  path.
+- After `await db.rollback()` do not read `current_user` or another loaded row; copy the id or email
+  into a local before the `try`.
+- Never log an email, token or CSRF value.
```
and in `skills/htmx-patterns/reference/testing.md`:
```diff
@@
 Use `httpx.AsyncClient` with `ASGITransport(app=app)` and override `current_active_user` and the
 session dependency through `app.dependency_overrides`; do not sign in through the login route in
 every test.
+
+A route whose error path rolls back needs one test with a real user row loaded through the route's
+own session (not the plain fake), that triggers the error and asserts the 4xx. A fake user cannot be
+expired by the rollback and hides `MissingGreenlet`.
```
Why: the same defect class recurred in four steps and the one that escaped two review rounds was invisible to fake-user tests; writing it down replaces the hand-carried prompt checklist. route.md goes to about 62 lines, over its 60 line cap, so the director should merge the new bullets with the existing ones (the first and last can fold into the CSRF and Errors bullets) when applying. testing.md is a second target of the same change.
