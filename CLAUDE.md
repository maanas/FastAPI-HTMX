# FastAPI-HTMX starter

Fork of Hybridhash/FastAPI-HTMX (`upstream`) at `github.com/maanas/FastAPI-HTMX` (`origin`). Goal: a
small, stable starter for our FastAPI sites. Open work and its order are in `TODO.md`.

## Tech Stack

- Python 3.12, FastAPI, SQLAlchemy 2 (async, SQLite locally), Alembic, fastapi-users, Pydantic v2
- Jinja2 templates with HTMX, Alpine.js, Tailwind CSS v4 and Flowbite v4
- `uv` for the virtualenv (poetry is not installed here; `pyproject.toml` is still poetry format)

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
theme/flowbite/            submodule, Flowbite v4.0.2, reference only, nothing loads from it
```

## Common Commands

```bash
uv venv --python 3.12 && uv pip install -r requirements.txt loguru pytest   # loguru is missing from requirements.txt
.venv/bin/python main.py                  # http://127.0.0.1:8080, needs .env (see README)
.venv/bin/python -m pytest -q app/tests
uvx ruff check <files>
.venv/bin/alembic revision --autogenerate -m "..." && .venv/bin/alembic upgrade head
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
`.claude/agents/` do the work and never delegate further.

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
root and are linked into `.claude/skills/` (`ln -s ../../skills/<name> .claude/skills/<name>`); edit
them in `skills/`. The ECC and team skills live directly in `.claude/skills/`.

A skill in `skills/` follows progressive disclosure: `SKILL.md` opens with an "Essentials" block of
at most 100 words that is enough for the common case, then a "Contents" table that says which
`reference/<topic>.md` to read and when. Detail goes in the reference files (one topic each, under
60 lines), never in `SKILL.md`. Read a reference file only when its row applies.

### Session and token budget

One task per session. When a task's pull request is open (or merged), write what is still open to
`TODO.md` and ask the user to `/clear` before the next task: every call resends the whole
conversation, so a long session is the main token cost. Past about 200k tokens of context, say so
and propose the clear at the next clean stop. After each commit, tell the user the hash and
whether this is a clean stop to clear at. Give subagents one step each, not a whole task. Tell a worker
which files to read; do not paste them into the prompt.

ECC skills are copied in by `~/bin/ecc.sh .` (plugin disabled for this project), listed in
`.claude/.ecc-manifest`. The team files (`coder`, `reviewer`, `checker`, `committer`, `retro`,
`commit`, `learning-report`, `pull-request`, the hooks) were adapted from
`~/Sites/minelytics/spider`.
