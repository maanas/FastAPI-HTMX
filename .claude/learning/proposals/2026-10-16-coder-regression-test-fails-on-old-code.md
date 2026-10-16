---
id: 2026-10-16-coder-regression-test-fails-on-old-code
status: applied
applied: 2026-10-16
target: .maanas/agents/coder.md
metric: tests
revises: 2026-10-13-coder-guard-tests-prove-themselves
---
Evidence: the applied rule covers only tests that scan templates. 2026-10-16 "MinIO off the event loop" step 1: the new thread test was not run against the old code by the coder or the reviewer (the reviewer argued it by reading); the director stashed `minio_core.py` and ran it (4 of 4 fail). Same gap earlier: 2026-10-13 "Hyperscript out" step 1 (new test passed with the wiring removed). Both cost director tokens or a fix round.
Change: widen the existing line instead of adding one (coder.md stays at 33 lines).
```diff
--- a/.maanas/agents/coder.md
+++ b/.maanas/agents/coder.md
@@
-- A test or guard that scans templates must be shown to work: give it one case it must flag (every attribute form the rule names) and one it must not (the word inside a string literal), and run it once with the change removed. Put a one-off assertion outside a parametrized test.
+- Every new test for a fix or a guard must be shown failing without the change: stash the changed source file, run the test, restore, and write the failing run in your report. A template scanner also gets one case it must flag (every attribute form the rule names) and one it must not (the word inside a string literal). Put a one-off assertion outside a parametrized test.
```
Why: a regression test that passes on the old code pins nothing, and reading cannot show it; the coder has the diff and the run is one command. Reviewer can then check the report line instead of repeating the run.
