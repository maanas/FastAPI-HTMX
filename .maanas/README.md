# .maanas

Project-owned Claude Code tooling for this repo: the dev team's agents and workflow skills. The
starter's app code never imports from here. Kept out of `.claude/.ecc-manifest`, so reversing
`~/bin/ecc.sh` leaves it untouched.

| Path | Purpose |
|---|---|
| `agents/` | Dev team: `coder`, `reviewer`, `retro` (Sonnet), `checker`, `committer` (Haiku) |
| `skills/` | Team workflow skills: `commit`, `pull-request`, `learning-report` |
| `skills/_template/` | Starting point for a new skill; never linked |
| `link.sh` | Symlinks root `skills/`, `.maanas/skills/` and `.maanas/agents/` into `.claude/` |

`.claude/agents/database-reviewer.md` and the reference skills in `.claude/skills/` are ECC copies
(listed in `.claude/.ecc-manifest`). The context guard hooks in `.claude/hooks/context-guard.sh`
and `resume-context.sh` are written by `ecc.sh` and overwritten on every run; `git-guard.sh` and
`protected-files.sh` are this repo's own.

New skill or agent:

    cp -r .maanas/skills/_template .maanas/skills/my-skill
    # edit .maanas/skills/my-skill/SKILL.md (name must match folder)
    .maanas/link.sh

`link.sh` never overwrites a real file and prunes dead links; safe to re-run.

## Scripts: Python, run with uv

Skill helpers live in `skills/<name>/scripts/*.py`, self-contained with PEP 723 inline metadata
(deps declared at the top of the file), run via `uv run <path>`. Scripts take CLI args and print
JSON (or `--out file`), so skills can chain them.
