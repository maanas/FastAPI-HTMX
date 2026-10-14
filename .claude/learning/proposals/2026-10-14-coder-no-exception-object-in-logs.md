---
id: 2026-10-14-coder-no-exception-object-in-logs
status: proposed
target: .claude/agents/coder.md
metric: security
---
Evidence: log 2026-10-14, task "htmx leftovers", step 3a: reviewer must-fix (security), `logger.opt(exception=error)` with loguru's default `diagnose=True` prints local variable values (form contents, CSRF token) and SQLAlchemy messages carry statement and parameters; cost a second review round and about 60k tokens. The existing rule "no secrets in logs" did not stop it. One occurrence, but the rule is cheap and the leak is severe.
Change:
```diff
--- a/.claude/agents/coder.md
+++ b/.claude/agents/coder.md
@@ -17,1 +17,2 @@
 - No secrets, `.env` contents or credentials in code, config or logs.
+- In a request path never pass an exception object or `exception=` to loguru: log the exception type and the route; database and validation errors by type only (messages hold statements, parameters and form values).
```
Why: names the concrete way request data reaches logs.
