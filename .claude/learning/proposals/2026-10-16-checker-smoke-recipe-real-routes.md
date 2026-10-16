---
id: 2026-10-16-checker-smoke-recipe-real-routes
status: applied
applied: 2026-10-16
target: .claude/agents/checker.md
metric: tokens:checker
revises: 2026-10-14-checker-login-recipe-jar-and-wait
---
Evidence: 2026-10-16 "Postgres and procrastinate" step 1 (checker 26k, login recipe wrong, page paths guessed) and step 2 (worker grep wrong). Earlier recipe proposals (2026-10-13-checker-smoke-login-recipe, 2026-10-14-checker-login-recipe-jar-and-wait, 2026-10-14-checker-placeholder-names-and-header-csrf) are applied, yet the recipe still says "take the `csrf_token` value from the HTML" and does not name the login route or pages.
Change (source path today: .claude/agents/checker.md; after PR #17: .maanas/agents/checker.md):
```diff
-take the `csrf_token` value from the HTML and unescape it (`&#43;` and friends, e.g. with `html.unescape`), POST it with that superuser into a cookie jar (`curl -c/-b`), then request the pages with the jar.
+take the token from the `data-csrf-token` attribute on `/login` and unescape it (`html.unescape`), POST the superuser as form fields `username` and `password` to `/auth/jwt/login` with `-b jar -c jar` and the header `X-CSRF-Token`, then request the pages with the jar. Page paths: `/user`, `/groups`, `/uploads`, `/role`; take others from `app/routes/view/`, never guess.
+For a procrastinate worker smoke, enqueue one job and look for "Success" in the worker log (not "succeeded").
```
Why: the recipe names what the app really does, so the checker stops rediscovering routes and log words.
