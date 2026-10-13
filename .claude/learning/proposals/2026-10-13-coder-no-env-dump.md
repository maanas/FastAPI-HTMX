---
id: 2026-10-13-coder-no-env-dump
status: applied
applied: 2026-10-13
target: .claude/agents/coder.md
metric: security
---
Evidence: log 2026-10-13, task "Templates to Flowbite v4 markup", step 4 (autoescape): the coder ran a bare `export`, which printed the whole shell environment, including an API key, into its transcript. The director then added "never run a bare export, env, set or printenv" to every later prompt by hand (steps 5 to 8). One incident, but a secret leak and a manual workaround repeated four times.
Change:
```diff
--- a/.claude/agents/coder.md
+++ b/.claude/agents/coder.md
@@
 - No secrets, `.env` contents or credentials in code, config or logs.
+- Never run a bare `export`, `env`, `set` or `printenv`: they print every secret in the shell. Read one variable by name (`printenv NAME` is also off limits for key-like names); set variables only inline on the command you run.
```
Why: puts the director's hand-written prompt line into the definition so it holds for every task. The same line belongs in `reviewer.md` (see the reviewer proposal) and `checker.md`; a PreToolUse hook that blocks these bare commands would enforce it and is worth the director's decision (hooks are outside this role's scope).
