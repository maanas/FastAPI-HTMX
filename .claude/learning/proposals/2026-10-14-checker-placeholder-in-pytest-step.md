---
id: 2026-10-14-checker-placeholder-in-pytest-step
status: applied
applied: 2026-10-14
target: .claude/agents/checker.md
metric: tokens:checker
---
Evidence: log 2026-10-14 "Housekeeping" step 2 (2 collection failures, CSRF and MINIO missing "despite placeholder rule") and 2026-10-14 "Permission type" step 1 (16 collection errors, re-run with placeholders). Revises 2026-10-14-checker-placeholder-default-and-zsh-names (applied): the rule sits inside step 4 (smoke), so the checker does not see it when it runs step 3 (pytest) first.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ step 3
-3. `.venv/bin/python -m pytest -q app/tests`, or only the tests the coder named when the step is small.
+3. `.venv/bin/python -m pytest -q app/tests`, or only the tests the coder named when the step is small. Set the settings first (prompt values, else the placeholder settings listed in step 4); a run without them fails at collection, so never run pytest bare.
```
Why: the placeholder rule is already there but only read at the smoke step; stating it at the pytest step stops the wasted first run twice seen.
