---
id: 2026-10-14-checker-placeholder-default-and-zsh-names
status: proposed
target: .claude/agents/checker.md
metric: tokens:checker
revises: 2026-10-14-checker-login-recipe-jar-and-wait
---
Evidence: log 2026-10-14, task "htmx leftovers", step 1 (checker first run PARTIAL, pytest and smoke SKIPPED for "no settings"; resumed with placeholders, 35,978 tokens, one extra round trip) and step 3b (self-inflicted retry: assigned the zsh read-only variable `GID`, server left running). The applied revision only covers "when the prompt asks for placeholder settings"; the same SKIPPED cost appeared in log 2026-10-13 "Browser pass" step 1. The zsh arrays proposal did not cover reserved names.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ 4. When templates, routes or static files changed
-when the prompt asks for placeholder settings, use them and run pytest, do not report SKIPPED)
+when the prompt gives no settings, use placeholder settings (throwaway values, scratch database) and run pytest and the smoke; never report SKIPPED for missing settings)
@@ `timeout` is not installed here
-The shell is zsh and does not split `$VAR`:
+The shell is zsh and does not split `$VAR`; never name a variable `GID`, `UID`, `EUID`, `status`, `path` or `pipestatus` (read-only or special), use `grp_id`, `user_id`, `code`:
```
Why: removes the round trip when the director forgets to say "placeholder settings", and a known zsh trap.
