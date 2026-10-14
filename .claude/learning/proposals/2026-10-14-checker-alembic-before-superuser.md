---
id: 2026-10-14-checker-alembic-before-superuser
status: proposed
target: .claude/agents/checker.md
metric: no such table: users
---
Evidence: log 2026-10-13 "Clean clone start" (checker failure "no such table: users") and 2026-10-14 "MinIO pass" step 1 (checker created the superuser on its scratch database before `alembic upgrade head`, login answered 500, rerun cost extra calls; checker 34,499 tokens, 20 tool uses).
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ step 4 @@
-For a page behind login: create a superuser in the scratch database with
+For a page behind login: first run `.venv/bin/alembic upgrade head` against the scratch database (same `DATABASE_URL` as the server), then create a superuser in it with
```
Why: a fresh scratch database has no tables, so the superuser step and login fail until the migration has run; stating the order removes the retry.
