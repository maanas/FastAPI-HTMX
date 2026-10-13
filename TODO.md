# TODO

Fork of Hybridhash/FastAPI-HTMX (`upstream`), kept at `github.com/maanas/FastAPI-HTMX` (`origin`,
SSH as `maanas`). Pull requests are opened by Claude on its own at the end of a task, with the `gh`
CLI and a full description (the `pull-request` skill): always `--repo maanas/FastAPI-HTMX --base
main`, because `gh` targets the upstream parent of a fork by default. Only maanas merges.
`gh` must be logged in as `maanas`; on 2026-10-13 the Mac Pro had only `kkuvam` (read-only on this
repo): run `gh auth login` as `maanas` once before the first pull request.
Goal (decided 2026-10-13): a basic working starter for our FastAPI apps on Tailwind CSS v4 +
Flowbite v4 + Alpine.js + HTMX with Jinja2. Its first user is medusa's app in the spider repo
(`~/Sites/minelytics/spider`, `medusa/app/`, step 2 in that repo's `TODO.md`), built from this
starter as a copy of the pattern once the starter works.

Rules from the owner: existing Flowbite components only, no custom layout; the whole design system
in variables in one place (colours are decided later, keep Flowbite's default theme); no CDN.

## State

- `main` equals upstream (4d8969e). Branch `chore/starter-setup` (local, not pushed) adds
  `theme/flowbite` (submodule, Flowbite v4.0.2: component markup in `content/components/*.md`,
  theme variables in `src/themes/`, app shell in `layouts/dashboard.html`; reference only, nothing
  loads from it at runtime) and this file.
- Committed on the branch (2026-10-13, not pushed): `.vscode/` removed; `CLAUDE.md`; `.claude/` with the ECC
  skills (`~/bin/ecc.sh`), the dev team adapted from the spider repo (`coder`, `reviewer`,
  `checker`, `committer`, `retro`, the `commit` and `learning-report` skills) and its two hooks, and
  four skills written for this repo: `flowbite` (component lookup in the submodule), `htmx-patterns`,
  `new-page` (these three in `skills/`, linked into `.claude/skills/`) and `pull-request`. There is no official Flowbite or htmx skill
  (checked 2026-10-13): Themesberg ships an MCP server (`npx flowbite-mcp`, needs Node) that covers
  what the submodule already holds; the htmx skills are third-party.
- The app was run once on 2026-10-13 in a scratch copy (uv, Python 3.12, SQLite). It starts and
  serves `/login`, `/register` and `/docs` after the fixes marked "found in the run" below. Login
  in a browser was not tried.

## Change list

- [x] **Run it as it is** (2026-10-13). Found in the run:
  - `requirements.txt` has no `loguru` (a dev dependency in `pyproject.toml`, imported by
    `main.py` and the app): `import app.app` fails.
  - No migration is committed. `alembic revision --autogenerate` writes one that fails on
    `alembic upgrade head` (`NameError: name 'app' is not defined`) until two imports are added by
    hand, as the README says.
  - `app/database/security.py` reads `AUTH_SECRET`, the README's `.env` sets `SECRET_KEY`: the
    auth secret is always `my_default_secret_key`.
  - `app/tests/test_view_crud.py` does not collect (`engine` is imported from `app.database.db`,
    it lives in `app.database.base`); the other 10 tests pass.
  - `app/static/js/htmx.min.js` is 1.9.6, the README says HTMX 2.
  - Startup creates `superuser@admin.com` / `password123` and logs the password.
  - `poetry` is not installed on the Mac Pro; `uv` is.
- [ ] **Make it start from a clean clone** (do first, small): `loguru` in the runtime
  dependencies, one committed initial migration (or the imports in `script.py.mako`), the
  `AUTH_SECRET` name in the README, the test import, uv instead of poetry, `.env.example`.
- [ ] **Assets off the CDNs** (`app/templates/base/auth_base.html` loads Flowbite 1.8.1 CSS and
  2.0.0 JS from cdnjs, Alpine `3.x.x` from jsdelivr, hyperscript from unpkg): vendor pinned
  Flowbite 4.0.2 JS, htmx 2.x and Alpine under `app/static/`, with a `VENDORED.md` (source,
  version, licence, sha256). The files come from the npm registry tarballs with curl, no Node.
- [ ] **CSS build**: Tailwind v4 with its standalone CLI, one tokens file with Flowbite's theme
  variables, built CSS committed. Open: whether Flowbite's Tailwind plugin (`theme/flowbite/plugin.js`)
  loads in the standalone CLI without `node_modules`; if not, say so before adding Node.
- [ ] **Templates to Flowbite v4 markup** (about 3,600 lines in `app/templates/`), `base.html` is an
  empty file: make it the generic shell (Flowbite navbar + sidebar).
- [ ] **Hyperscript out**: 5 templates still use it; move them to Alpine and drop the library.
- [ ] **Alpine CSP build** (`@alpinejs/csp`) if the 11 `x-data` uses can live in `Alpine.data()`
  components, so the content security policy needs no `unsafe-eval`. Not tried yet.
- [ ] **Security**: `app/database/security.py` logs the auth secret (`logger.critical(SECRET)`) and
  defaults it to `my_default_secret_key`: remove the log, refuse to start on the default. The
  superuser comes from the environment or a command, not a fixed password at startup. Add
  security headers with a strict content security policy (own origin only, no inline script).
  htmx: `allowEval=false`, `includeIndicatorStyles=false`, `selfRequestsOnly=true`.
- [ ] **Housekeeping**: static and template paths relative to the package (today relative to the
  working directory), a LICENSE file (the README says MIT, the repo has none: ask upstream or
  state it for our changes), ruff and pytest brought up to date (ruff is pinned at 0.0.291), `setup.ps1` and the Windows path
  in the README, `@app.on_event` to a lifespan handler, tests (3 files today).
- [ ] **Decide what medusa takes**: the folder pattern (`routes/view`, `routes/api`,
  `templates/{base,pages,partials}`), the shell and the asset build; users, roles, groups, MinIO
  and CSRF only when medusa gets its first write action (its login may be Tailscale identity).
