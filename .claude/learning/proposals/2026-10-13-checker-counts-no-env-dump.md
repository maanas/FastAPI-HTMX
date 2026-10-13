---
id: 2026-10-13-checker-counts-no-env-dump
status: applied
applied: 2026-10-13
target: .claude/agents/checker.md
metric: tests
---
Evidence: log 2026-10-13, task "Templates to Flowbite v4 markup": test counts reported by workers were wrong twice (step 5 reviewer said 70 against 60; step 7 coder said "21 new" against 19), and the director began asking for `pytest --collect-only -q` counts by hand. Checker runs also wrote `.pyc` files and reused an older scratch database by accident (minor). Step 4 incident of a bare `export` dumping the environment applies to this role too.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@
-Report: PASS, FAIL, PRE-EXISTING or ERROR.
+Never run a bare `export`, `env`, `set` or `printenv`. Run pytest with `PYTHONDONTWRITEBYTECODE=1` and a fresh scratch database path under the scratchpad directory.
+
+Run `.venv/bin/python -m pytest --collect-only -q app/tests` and report the collected count per test file and the total, plus passed and failed counts; the director takes test counts from this report only.
+
+Report: PASS, FAIL, PRE-EXISTING or ERROR.
```
Why: one authoritative test count removes the repeated miscounts and the manual follow-up, and the two env lines stop the stray files and stale database. The scratch database clause assumes the prompt's settings name the database; if they do not, drop that half.
