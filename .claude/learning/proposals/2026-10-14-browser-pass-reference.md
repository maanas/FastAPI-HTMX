---
id: 2026-10-14-browser-pass-reference
status: applied
applied: 2026-10-14
target: skills/htmx-patterns/reference/browser-pass.md
metric: correctness
---
Evidence: log 2026-10-13, task "Browser pass", steps 1 and 2: a director-run browser pass found nine real bugs that 415 tests and three earlier reviews missed, and step 2's reviewer medium (auto-hide on a watcher) was behaviour only a browser shows (no JS runner, components.js has substring tests). The method was learned by trial: Chrome extension not connected at first, native confirm() invisible, coordinate clicks landing wrong after a late resize, `ls .env` and moving users.db denied.
Change: new file (and one row in the Contents table of skills/htmx-patterns/SKILL.md: `reference/browser-pass.md` | Checking a page or a swapped partial in a real browser). Under 60 lines:
```diff
--- /dev/null
+++ b/skills/htmx-patterns/reference/browser-pass.md
@@
+# Browser pass (director only; workers have no browser)
+
+- Needs the Claude in Chrome extension connected (`/chrome`, restart the session if tools are missing).
+- Use a scratch database: `DATABASE_URL` pointing at a file under the scratchpad plus throwaway
+  settings there; never move or delete `users.db`, never touch `.env`.
+- Native `confirm()` is invisible to the extension. Replace `window.confirm` with a stub that records
+  the text and returns true or false; `hx-confirm` calls it, so both answers can be tested.
+- Resize to phone width, then wait; prefer `javascript_tool` (`element.click()`, reading Alpine data,
+  `input.validity`) over clicks by coordinate.
+- Check the console on every page: no CSP violation, no "CSP Parser Error", no "Undefined variable".
+- Test repeated identical errors, stale messages after a fix, and each status (400, 403, 422, network).
+- Anything needing a service (MinIO, Docker) that is down goes to TODO.md as untested.
```
Why: a repeatable method for the bug class the suite and reviewers cannot see, instead of rediscovering it each task.
