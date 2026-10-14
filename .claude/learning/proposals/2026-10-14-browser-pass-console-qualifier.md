---
id: 2026-10-14-browser-pass-console-qualifier
status: applied
applied: 2026-10-14
target: skills/htmx-patterns/reference/browser-pass.md
metric: correctness
---
Evidence: log 2026-10-14, task "htmx leftovers", director browser pass: htmx logs "Response Status Error Code 4xx" to the console for every swapped error answer (expected), so the rule "no console error" is wrong as written. Also a successful delete alert uses the danger colours of an error alert (open observation, goes to TODO.md, not this proposal). Related applied: 2026-10-14-browser-pass-reference.
Change:
```diff
--- a/skills/htmx-patterns/reference/browser-pass.md
+++ b/skills/htmx-patterns/reference/browser-pass.md
-- Check the console on every page: no CSP violation, no "CSP Parser Error", no "Undefined variable".
+- Check the console on every page: no CSP violation, no "CSP Parser Error", no "Undefined variable". htmx's "Response Status Error Code 4xx" for a swapped error answer is expected.
```
Why: stops a false alarm in every pass that tests an error status.
