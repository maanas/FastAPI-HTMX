---
id: 2026-10-16-checker-postgres-scratch-db
status: applied
applied: 2026-10-16
target: .claude/agents/checker.md
metric: correctness
---
Evidence: 2026-10-16 "Postgres and procrastinate" steps 1 and 2: the starter is Postgres only (commit 8e24e00), checker.md lines 14 and 18 still say "local SQLite file" and "scratch database path under the scratchpad". The checker had to improvise a scratch database both steps.
Change (source path today: .claude/agents/checker.md; after PR #17: .maanas/agents/checker.md):
```diff
-Never edit files, never touch a database other than the local SQLite file, never ssh.
+Never edit files, never ssh. The only database you touch is a scratch one on the compose db (127.0.0.1:5434): create `smoke_<hex>` and drop it when done, both through `docker compose exec db psql`. pytest makes and drops its own `pytest_<hex>` database.
-Run pytest with `PYTHONDONTWRITEBYTECODE=1` and a fresh scratch database path under the scratchpad directory.
+Run pytest with `PYTHONDONTWRITEBYTECODE=1`; the smoke server's `DATABASE_URL` points at the `smoke_<hex>` database.
```
Why: removes the stale SQLite rule so the checker has one stated way to get a scratch database.
