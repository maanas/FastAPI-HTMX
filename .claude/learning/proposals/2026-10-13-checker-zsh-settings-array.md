---
id: 2026-10-13-checker-zsh-settings-array
status: applied
applied: 2026-10-13
target: .claude/agents/checker.md
metric: tokens:checker
---
Evidence: log 2026-10-13, "Security" step 1: checker 43,827 tokens, 24 tool uses; its own note says the first lint and pytest runs used settings and a file list held in string variables, which zsh does not word-split, plus a malformed DATABASE_URL; it discarded and reran. Step 3 had smaller checker cost (42,583) but the pattern is a known zsh trap on this Mac. One occurrence, costly, cheap to prevent.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ -16 +16 @@
-`timeout` is not installed here: run pytest without it, and stop a background server by its PID (`$!`), never by name.
+`timeout` is not installed here: run pytest without it, and stop a background server by its PID (`$!`), never by name. The shell is zsh and does not split `$VAR`: keep settings and file lists in arrays (`settings=(A=1 B=2); env "${settings[@]}" cmd`, `files=(a.py b.py); uvx ruff check "${files[@]}"`).
```
Why: avoids a discarded first run of lint and pytest.
