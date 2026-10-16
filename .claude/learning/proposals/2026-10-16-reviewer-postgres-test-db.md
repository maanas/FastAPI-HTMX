---
id: 2026-10-16-reviewer-postgres-test-db
status: applied
applied: 2026-10-16
target: .claude/agents/reviewer.md
metric: tests
---
Evidence: 2026-10-16 "Postgres and procrastinate": reviewer.md line 9 asks for "a fresh DATABASE_URL sqlite path under the scratchpad directory"; conftest.py now makes its own `pytest_<hex>` database on the compose db and rejects other URLs.
Change (source path today: .claude/agents/reviewer.md; after PR #17: .maanas/agents/reviewer.md):
```diff
-and a fresh `DATABASE_URL` sqlite path under the scratchpad directory; `conftest.py` sets `AUTH_SECRET`.
+and the compose `DATABASE_URL` (127.0.0.1:5434); `conftest.py` creates and drops its own `pytest_<hex>` database and sets `AUTH_SECRET`. If the db is down, say "tests not run: db down".
```
Why: a sqlite path now fails the conftest URL guard, so the reviewer would report "tests not run" for no reason.
