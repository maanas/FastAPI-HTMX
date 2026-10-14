---
id: 2026-10-14-checker-no-env-existence-check
status: applied
applied: 2026-10-14
target: .claude/agents/checker.md
metric: env
revises: 2026-10-13-checker-env-vars-ok
---
Evidence: `ls .env` was attempted and denied by the permission system in 2026-10-13 "Make it start from a clean clone" step 1, and again in 2026-10-14 "Housekeeping" step 1, although checker.md already says "Never `ls` the repo root or `.env`" (applied 2026-10-13). The ban is a rule about commands, the checker still wants to know whether `.env` exists. Nothing was read, but each denial costs a turn.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ line 14
-A missing `.env` is not an error when the prompt supplies the settings as environment variables: use them.
+Do not test whether `.env` exists, in any command (not `ls`, `test -f`, `stat`, `find`, `cat`); the prompt's settings or the placeholder settings are the only source, and `.env` is never consulted.
```
Why: removes the reason to probe instead of repeating the command ban that failed twice.
