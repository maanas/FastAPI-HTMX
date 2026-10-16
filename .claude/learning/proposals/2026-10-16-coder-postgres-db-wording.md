---
id: 2026-10-16-coder-postgres-db-wording
status: applied
applied: 2026-10-16
target: .claude/agents/coder.md
metric: correctness
---
Evidence: 2026-10-16 "Postgres and procrastinate", step 1: coder.md line 23 says "never touch a database other than the local SQLite file"; the app no longer has one. The coder rightly did not edit agent files, but the rule now forbids every database.
Change (source path today: .claude/agents/coder.md; after PR #17: .maanas/agents/coder.md):
```diff
-Never ssh, never deploy, never touch a database other than the local SQLite file.
+Never ssh, never deploy, never touch a database other than the compose db on 127.0.0.1:5434 (scratch databases `smoke_<hex>` only, made and dropped through `docker compose exec db psql`).
```
Why: the rule matches the real database, so the coder can run its own smoke without breaking it.
