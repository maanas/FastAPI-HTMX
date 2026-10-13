---
id: 2026-10-14-checker-login-recipe-jar-and-wait
status: proposed
target: .claude/agents/checker.md
metric: tokens:checker
revises: 2026-10-13-checker-smoke-login-recipe
---
Evidence: log 2026-10-13, task "Browser pass", step 1 (checker 50,938 tokens, 39 tool uses: first role POST failed on its own CSRF cookie handling; unsure whether "no settings means SKIPPED" applied when the prompt asked for placeholder settings, made up values) and step 2 (37,035 tokens, 17 uses: two server starts failed, readiness probe too fast, CSRF cookie not saved to the jar on GET /login). The recipe applied in 2026-10-13-checker-smoke-login-recipe covers the token and unescape but not these two points, and the same recipe still cost time in two more runs.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@
-keep `$!`, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8091<path>` for each page,
+keep `$!`, wait until `curl -s -o /dev/null http://127.0.0.1:8091/login` succeeds (retry up to 15 times, 1 s apart) before any request, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8091<path>` for each page,
@@
-GET `/login`, take the `csrf_token` value
+GET `/login` with `-c jar` (the CSRF cookie is set there; the POST must send `-b jar -c jar` and the token in the form), take the `csrf_token` value
@@
-values from the prompt or made up for the run)
+values from the prompt or made up for the run; when the prompt asks for placeholder settings, use them and run pytest, do not report SKIPPED)
```
Why: removes the two start-up failures and the SKIPPED doubt that cost the checker retries in both steps.
