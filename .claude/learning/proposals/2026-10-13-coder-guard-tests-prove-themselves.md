---
id: 2026-10-13-coder-guard-tests-prove-themselves
status: applied
applied: 2026-10-13
target: .claude/agents/coder.md
metric: tests
---
Evidence: category `tests` findings on template guards and scanners in three tasks. 2026-10-13 "Templates to Flowbite v4 markup" step 1 (scanner missed `style=` and `on*=`), step 2 (regex scanner stopped at first `>`); "Hyperscript out" step 1 (new test passes with the wiring removed); "Alpine CSP build" step 1 (guard missed `x-html`, matched `window` and `;` inside string literals, assertion inside a parametrized test ran per parameter).
Change:
```diff
--- a/.claude/agents/coder.md
+++ b/.claude/agents/coder.md
@@
 - Do not commit or push.
+- A test or guard that scans templates must be shown to work: give it one case it must flag (every attribute form the rule names) and one it must not (the word inside a string literal), and run it once with the change removed. Put a one-off assertion outside a parametrized test.
```
Why: four tests findings in three tasks were weak guards (false negatives and positives), each costing a fix round; a must-flag and must-pass case catches both. coder.md goes from 29 to 30 lines.
