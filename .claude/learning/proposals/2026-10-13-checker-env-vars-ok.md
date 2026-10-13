---
id: 2026-10-13-checker-env-vars-ok
status: proposed
target: .claude/agents/checker.md
metric: env
revises: 2026-10-13-checker-env-probes
---
Evidence: log 2026-10-13, "Make it start from a clean clone" steps 1 and 3 (env failures), then "CSS build" step 1: the applied probe change worked (no denied calls), but the checker still stops with ERROR when `.env` is absent, although workers are meant to get the ten settings as environment variables (TODO.md). Result: pytest reported ERROR and the director reran it by hand (15 passed). Third env-family failure.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@
-If `.venv` is missing (`test -d .venv`) or `.env` is missing (`test -f .env && echo present`), report ERROR with the setup lines from CLAUDE.md; do not create them.
+If `.venv` is missing (`test -d .venv`), report ERROR with the setup lines from CLAUDE.md; do not create it. A missing `.env` is not an error when the prompt supplies the settings as environment variables: use them. Without both, run steps 1, 2 and 4 and report pytest as SKIPPED (no settings), not ERROR.
```
Why: a missing `.env` is an environment gap, not a code failure; the checker should use supplied variables and still run the other checks.
