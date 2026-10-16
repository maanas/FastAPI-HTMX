---
id: 2026-10-16-checker-secret-values-no-placeholder-word
status: applied
target: .claude/agents/checker.md
metric: tokens:checker
---
Evidence: log 2026-10-14 (Permission type, step 1: pytest without settings, rerun with placeholders) led to applied proposals 2026-10-14-checker-placeholder-*. Since then 2026-10-16 "Jobs follow-ups" step 1: checker still retried because AUTH_SECRET and CSRF_SECRET_KEY values contained "placeholder" and the validator rejects that. The checker file calls the throwaway values "placeholder settings", which invites that word in the values. Revises 2026-10-14-checker-placeholder-default-and-zsh-names.
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ step 4
-AUTH_SECRET must not be the example placeholder, the app rejects it)
+AUTH_SECRET and CSRF_SECRET_KEY must be random-looking throwaway strings (for example `openssl rand -hex 16`); the validator rejects any value containing the word "placeholder", so never put it in a value)
```
Why: the retry costs a full checker run each time; naming the forbidden word and a safe generator removes it.
