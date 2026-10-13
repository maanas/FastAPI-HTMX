---
id: 2026-10-13-checker-smoke-login-recipe
status: applied
applied: 2026-10-13
target: .claude/agents/checker.md
metric: tokens:checker
---
Evidence: log 2026-10-13, task "Hyperscript out", step 1: checker used 51,959 tokens and 33 tool uses (coder 37,998, reviewer 41,477). Its notes: login helper failed twice (CSRF token is HTML-escaped in the login page; output mixed into the token variable), and a server started inside a shell function survived the kill, so `$!` was not its PID (found by port, PID 44887); `main.py` hardcodes port 8080 with reload, so it ran uvicorn on 8091. Earlier authenticated smoke steps were also the costliest checker runs: "Templates to Flowbite v4 markup" steps 3, 5, 6, 7 (53k, 59k, 101k, 158k). The applied proposal 2026-10-13-checker-env-probes (stop by PID) did not cover a server started inside a function.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@
-Start the server with `.venv/bin/python main.py` in the background, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080<path>` for each page, then stop the server.
+Start the server at top level, not inside a shell function: `.venv/bin/python -m uvicorn app.app:app --port 8091 &`, keep `$!`, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8091<path>` for each page, then `kill` that PID (if lost, `lsof -ti :8091`). For a page behind login: GET `/login`, take the `csrf_token` value from the HTML and unescape it (`&#43;` and friends, e.g. with `html.unescape`), POST it with the seeded superuser into a cookie jar (`curl -c/-b`), then request the pages with the jar. Put each value in its own variable; never print cookies or tokens.
```
Why: the login and server-stop steps cost the checker repeated trial and error; one written recipe removes it. The rule 4 line change is a merge into the existing step, so the file stays near 22 lines.
