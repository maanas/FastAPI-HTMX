---
id: 2026-10-13-reviewer-run-tests-without-prompt-settings
status: applied
applied: 2026-10-13
target: .claude/agents/reviewer.md
metric: tests
revises: 2026-10-13-reviewer-readonly-and-verify
---
Evidence: log 2026-10-13, "Templates to Flowbite v4 markup" steps 1 and 2 (reviewer could not run pytest, no settings) led to the applied rule "say tests not run". Task "Security", all three steps (five review prompts): the reviewer again ran no tests ("the prompt did not supply the settings"). Its step 2 finding that logout broke was green in the suite, and step 1 tests were judged by reading. The applied rule turned a manual director chore into a silent skip, so it did not work.
Change:
```diff
--- a/.claude/agents/reviewer.md
+++ b/.claude/agents/reviewer.md
@@ -9 +9 @@
-Run the tests the coder named with `.venv/bin/python -m pytest -q <tests>` when the prompt supplies the settings as environment variables; without them say "tests not run" instead of judging them by reading. When a security ...
+Run the tests the coder named with `.venv/bin/python -m pytest -q <tests>`, `PYTHONDONTWRITEBYTECODE=1`. If the prompt supplies no settings, use the placeholder values in `.env.example` (never `.env`) and a fresh `DATABASE_URL` sqlite path under the scratchpad directory; `conftest.py` sets `AUTH_SECRET`. Say "tests not run" only if that fails. When a security ...
```
Why: the settings are all placeholders plus a scratch database, so the reviewer can build them itself instead of depending on each prompt.
