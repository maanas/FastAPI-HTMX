---
id: 2026-10-13-reviewer-readonly-and-verify
status: proposed
target: .claude/agents/reviewer.md
metric: correctness
---
Evidence: log 2026-10-13, task "Templates to Flowbite v4 markup". Step 7: the reviewer ran `git stash` and `git stash pop` (read-only role, tree restored by luck). Steps 1 and 2: the reviewer could not run pytest (no settings) and judged tests by reading; from step 3 the director gave it the settings and it ran the suite. Step 1: the reviewer stated `{{ message }}` was autoescaped without reading `app/templates.py`; autoescape was off, found two steps later by a coder (step 4 was added for it). Step 4 coder also ran a bare `export` (see 2026-10-13-coder-no-env-dump).
Change:
```diff
--- a/.claude/agents/reviewer.md
+++ b/.claude/agents/reviewer.md
@@
-Never edit files and never start a server.
+Never edit files and never start a server. Use only read-only git (`diff`, `log`, `show`, `status`); never `stash`, `checkout`, `reset`, `add` or anything else that changes the tree or index. Never run a bare `export`, `env`, `set` or `printenv`.
+
+Run the tests the coder named with `.venv/bin/python -m pytest -q <tests>` when the prompt supplies the settings as environment variables; without them say "tests not run" instead of judging them by reading. When a security or correctness finding (or its absence) rests on a framework default, such as Jinja autoescape, CSRF or cookie flags, read the config that sets it and cite the file and line.
```
Why: a read-only role must not touch the tree, and an approval that relies on an unchecked default cost an extra step; running the suite catches what reading cannot. The file stays at about 26 lines.
