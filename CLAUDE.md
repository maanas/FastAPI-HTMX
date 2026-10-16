# FastAPI-HTMX starter

Fork of Hybridhash/FastAPI-HTMX (`upstream`) at `github.com/maanas/FastAPI-HTMX` (`origin`). Goal: a
small, stable starter for our FastAPI sites. Open work and its order are in `TODO.md`.

## Tech Stack

- Python 3.12, FastAPI, SQLAlchemy 2 (async, SQLite locally), Alembic, fastapi-users, Pydantic v2
- Jinja2 templates with HTMX, Alpine.js, Tailwind CSS v4 and Flowbite v4
- `uv` manages dependencies: `pyproject.toml` pins them, `uv.lock` locks them, `uv sync` creates `.venv`
  (runtime plus the dev group with pytest and ruff)

## Project Structure

```
app/app.py                 FastAPI app, routers, static mount
app/routes/view/           page and partial routes (HTML)
app/routes/api/            JSON routes
app/models/  app/schema/   SQLAlchemy models, Pydantic schemas
app/database/              engine, session, auth (fastapi-users)
app/templates/{base,pages,partials}/
app/static/                vendored JS, built CSS, images
app/migrations/            Alembic
app/tests/                 pytest
skills/                    this repo's own skills, linked into .claude/skills/
.maanas/                   dev team agents and workflow skills, linked into .claude/ (see its README)
theme/flowbite/            submodule, Flowbite v4.0.2, reference only, nothing loads from it
```

## Common Commands

```bash
uv sync                                   # .venv from uv.lock
cp .env.example .env                      # then edit it (see README)
.venv/bin/alembic upgrade head            # create or update the database
.venv/bin/python main.py                  # http://127.0.0.1:8080
.venv/bin/python -m app.commands.create_superuser   # create or promote a superuser
.venv/bin/python -m pytest -q app/tests   # builds its own throwaway database; needs the other settings
uvx ruff check <files>
tools/css.sh [--watch]                    # rebuild app/static/css/app.css (Tailwind, no Node)
.venv/bin/alembic revision --autogenerate --rev-id 0002_<what> -m "<what>"   # next migration, see app/migrations/README
```

## Rules

- UI is existing Flowbite components only, no custom layout. Markup comes from
  `theme/flowbite/content/components/<name>.md`; Grep it, never read `theme/flowbite/llms-full.txt`
  (2.8 MB). Never edit the submodule.
- The whole design system sits in variables in one tokens file. Colours are decided later: keep
  Flowbite's default theme.
- No CDN. Every script and stylesheet is vendored under `app/static/` and listed in `VENDORED.md`.
- No inline script, inline style or `on*=` handler in templates; no hyperscript.
- An HTMX request gets a partial, a full request gets a page.
- A model change ships with its migration and its import in `init_models`.
- No secrets in code, config or logs. `.env` is never read or edited by Claude.
- No em dashes or smart quotes in code, docs or commits. No AI attribution in commits.

## Orchestration

The main session directs: it plans, delegates, reads reports and decides. Workers in
`.maanas/agents/` (linked into `.claude/agents/`) do the work and never delegate further.

| Agent | Model | Job |
|---|---|---|
| `coder` | Sonnet | Implements one planned step; never commits |
| `reviewer` | Sonnet | Read-only review of the step's diff: correctness, security, UI rules |
| `checker` | Haiku | `ruff check` on changed files, `py_compile`, pytest, smoke request per touched page |
| `committer` | Haiku | Local commit in the repo's style (`commit` skill) |
| `retro` | Sonnet | End of task: logs the task to `.claude/learning/log.jsonl`, drafts proposals |
| `database-reviewer` | Sonnet | On request, for schema, migration and query changes |

Per task: the director creates a feature branch from `main`. Per step: coder, reviewer (fix loop at
most 2 rounds, then escalate), checker, committer. The director keeps a ledger per step: each
report, review rounds, escalations, the user's corrections in chat, and the tokens per agent from
the task notifications. After the last commit, the director gives the ledger to `retro`, shows the
user each new proposal in `.claude/learning/proposals/`, and applies only the approved ones (see
the `learning-report` skill). Agents, skills and tools change only through an approved proposal.
When the task is done, the director runs the `pull-request` skill on its own: it pushes the branch
and opens the pull request on the fork with `gh` (logged in as `maanas`) and a full description.
Only maanas merges: never merge or approve a pull request, never push to `main` directly.

`.claude/hooks/git-guard.sh` blocks commits and merges on `main`, pushes to `main`, force pushes
and `--no-verify`. `.claude/hooks/protected-files.sh` blocks edits to `.env` files.

### Project skills

| Skill | Use |
|---|---|
| `flowbite` | Find one component's markup, theme variables or JS behaviour in the submodule |
| `htmx-patterns` | Partial versus page, swaps, CSRF, status codes, Flowbite and Alpine after a swap, CSP |
| `new-page` | Recipe for a page: route, template, partials, registration, test |
| `commit`, `pull-request`, `learning-report` | Team workflow |

Skills written for this repo (`flowbite`, `htmx-patterns`, `new-page`) live in `skills/` at the repo
root; the team skills (`commit`, `pull-request`, `learning-report`) and the agents live in
`.maanas/`. `.maanas/link.sh` links all of them into `.claude/`; edit them at the source. The ECC
skills live directly in `.claude/skills/`.

A skill in `skills/` follows progressive disclosure: `SKILL.md` opens with an "Essentials" block of
at most 100 words that is enough for the common case, then a "Contents" table that says which
`reference/<topic>.md` to read and when. Detail goes in the reference files (one topic each, under
60 lines), never in `SKILL.md`. Read a reference file only when its row applies.

### Session and token budget

One task per session. When a task's pull request is open (or merged), write what is still open to
`TODO.md` and ask the user to `/clear` before the next task: every call resends the whole
conversation, so a long session is the main token cost. Auto-compaction runs at 100k tokens
(`autoCompactWindow` in `.claude/settings.json`); after it the SessionStart `compact` hook
(`.claude/hooks/resume-context.sh`) re-injects the branch, git state and `TODO.md` above
`## Done`, so `TODO.md` is the only state that survives. The context guard
(`.claude/hooks/context-guard.sh`, `CONTEXT_LIMIT`, default 85k) warns from 85k: write the state
to `TODO.md` first (step ledger included), then continue, and propose the clear at the next
clean stop. Both hooks are written by `ecc.sh`; fix them there, not here. After each commit, tell the user the hash and
whether this is a clean stop to clear at. Give subagents one step each, not a whole task. Tell a worker
which files to read; do not paste them into the prompt.

ECC skills are copied in by `~/bin/ecc.sh . web` (plugin disabled for this project), listed in
`.claude/.ecc-manifest`. The team files (`coder`, `reviewer`, `checker`, `committer`, `retro`,
`commit`, `learning-report`, `pull-request`, the hooks) were adapted from
`~/Sites/minelytics/spider`.

<!-- ecc.sh:rules:start - managed by ~/bin/ecc.sh; edits inside this block are overwritten -->
## Hard Limits
- Functions: <= 100 lines
- Cyclomatic complexity: <= 8
- Positional parameters: <= 5
- Line length: 100 characters
- Files: <= 500 lines

## Python Tooling
- Package manager: uv
- Linting + formatting: ruff
- Type checking: ty, where the project has it set up
- Testing: pytest
- Run commands: `uv run <tool>`, unless the project section of CLAUDE.md names another form
  (e.g. `.venv/bin/<tool>`); the project section wins
- Skill helper scripts: PEP 723 single files, `uv run <path>` (see `.maanas/README.md`)

## Behavioral Rules
- NEVER create files unless absolutely necessary
- ALWAYS read a file before editing it
- ALWAYS prefer editing existing files to creating new ones
- NEVER commit secrets, credentials, or .env files
- No AI attribution in commits or PRs (no Co-Authored-By, no "Generated with")

## Error Handling
- Fail fast with clear, actionable messages
- Never swallow exceptions silently
- Include context (what operation, what input, suggested fix)

## Session state
- `TODO.md` is the only state that survives auto-compaction (at 100k tokens; the SessionStart
  compact hook re-injects it). Treat it as the state capture, not just a build order.
- Layout: `## State` (one `Next:` line with files and next step, what is in progress, decisions
  and notes), then `## Pending` (open items by phase), then `## Done` (finished items by phase).
  Only State and Pending are re-injected; Done is read on demand.
- Update it as you work, not at the end: move finished items from Pending to Done, keep `Next:`
  and the decisions current.
- When the context-guard hook reports the budget, write the state to `TODO.md` before anything else.

## Approach
- Think before acting. Read existing files before writing code.
- Be concise in output but thorough in reasoning.
- Prefer editing over rewriting whole files.
- Do not re-read files you have already read unless the file may have changed.
- Test your code before declaring done.
- No sycophantic openers or closing fluff.
- Keep solutions simple and direct.
- User instructions always override this file.

## Code Rules
- Simplest working solution. No over-engineering.
- No abstractions for single-use operations.
- No speculative features or "you might also want..."
- No docstrings or type annotations on code not being changed.
- No error handling for scenarios that cannot happen.
- Three similar lines is better than a premature abstraction.

## Review Rules
- State the bug. Show the fix. Stop.
- No suggestions beyond the scope of the review.
- No compliments on the code before or after the review.

## Debugging Rules
- Never speculate about a bug without reading the relevant code first.
- State what you found, where, and the fix. One pass.
- If cause is unclear: say so. Do not guess.

## Formatting
- No em dashes, smart quotes, or decorative Unicode symbols.
- Plain hyphens and straight quotes only.
- Natural language characters (accented letters, CJK, etc.) are fine when the content requires them.
- Code output must be copy-paste safe.

## Output
- Return code first. Explanation after, only if non-obvious.
- No inline prose. Use comments sparingly - only where logic is unclear.
- No boilerplate unless explicitly requested.
<!-- ecc.sh:rules:end -->
