---
id: 2026-10-13-coder-stop-server-by-pid
status: applied
applied: 2026-10-13
target: .claude/agents/coder.md
metric: correctness
---
Evidence: log 2026-10-13, task "Make it start from a clean clone", step 5: coder stopped its server with `pkill -f "app.app:app|main.py"`, which matches by name on the owner's machine. Step 2: coder only exercised GET pages after a framework upgrade, and the reviewer found the POST/auth flows and two older bugs (not yet a repeat, noted for watching).
Change:
```diff
--- a/.claude/agents/coder.md
+++ b/.claude/agents/coder.md
@@
-- You may run `uvx ruff check <files>`, `.venv/bin/python -m pytest <tests>` and a local server on 127.0.0.1 that you stop before you report.
+- You may run `uvx ruff check <files>`, `.venv/bin/python -m pytest <tests>` and a local server on 127.0.0.1 that you stop before you report. Start it in the background, keep its PID (`$!`) and `kill` that PID; never `pkill` or `killall` by name.
```
Why: name-based kills can end the owner's unrelated processes; a PID kill is as short and safe.
