---
id: 2026-10-14-coder-ruff-after-fix-and-keep-guards
status: applied
applied: 2026-10-14
target: .claude/agents/coder.md
metric: tests
---
Evidence: log 2026-10-14, task "htmx leftovers", step 3b: reviewer must-fix (tests) because the coder rewrote two security guard tests ("no data after a refused CSRF check") to a weaker meaning, left a non-superuser path on the update routes untested, and closed a real leak without a test; the same step then failed the checker on a new E501 in a docstring edited in the fix round, after the coder's own ruff run. Related applied: 2026-10-13-coder-guard-tests-prove-themselves (guards that scan templates), which does not cover rewriting an existing test.
Change:
```diff
--- a/.claude/agents/coder.md
+++ b/.claude/agents/coder.md
@@ -26,2 +26,4 @@
 - A test or guard that scans templates must be shown to work: ...
+- Changing an existing test: write the old guarantee in your report and keep a test for it; a behaviour you change on the way (a leak you close) gets its own test.
+- Run `uvx ruff check` on the changed files again after every fix round, docstring edits included.
```
Why: both were caught late (reviewer round 1, checker FAIL) and cost a round each.
