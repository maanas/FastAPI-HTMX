---
id: 2026-10-13-checker-env-probes
status: applied
applied: 2026-10-13
target: .claude/agents/checker.md
metric: tokens:checker
---
Evidence: log 2026-10-13, task "Make it start from a clean clone", step 1 (`ls .env` denied, `timeout` not installed) and step 3 (`ls -a` listed `.env` entries). Same kind of failure twice: the checker probes for `.env` by listing it, and its pytest line needs `timeout`, which is absent on this Mac.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@
-If `.venv` or `.env` is missing, report ERROR with the setup lines from CLAUDE.md; do not create them. Never edit files, ...
+If `.venv` is missing (`test -d .venv`) or `.env` is missing (`test -f .env && echo present`), report ERROR with the setup lines from CLAUDE.md; do not create them. Never `ls` the repo root or `.env`, never read `.env`. Never edit files, ...
@@
-Run the tests under `timeout 300`.
+`timeout` is not installed here: run pytest without it, and stop a background server by its PID (`$!`), never by name.
```
Why: removes two wasted or denied calls per run and keeps `.env` handling inside CLAUDE.md rules.
