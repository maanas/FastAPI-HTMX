# TODO

Fork of Hybridhash/FastAPI-HTMX (`upstream`), kept at `github.com/maanas/FastAPI-HTMX` (`origin`,
SSH as `maanas`). Pull requests are opened by Claude on its own at the end of a task, with the `gh`
CLI and a full description (the `pull-request` skill): always `--repo maanas/FastAPI-HTMX --base
main`, because `gh` targets the upstream parent of a fork by default. Only maanas merges.
`gh` on the Mac Pro is logged in as `maanas` (active, admin on this repo) and `kkuvam` (read-only
here); the skill checks the active account and switches to `maanas`.
Goal (decided 2026-10-13): a basic working starter for our FastAPI apps on Tailwind CSS v4 +
Flowbite v4 + Alpine.js + HTMX with Jinja2. Its first user is medusa's app in the spider repo
(`~/Sites/minelytics/spider`, `medusa/app/`, step 2 in that repo's `TODO.md`), built from this
starter as a copy of the pattern once the starter works.

Rules from the owner: existing Flowbite components only, no custom layout; the whole design system
in variables in one place (colours are decided later, keep Flowbite's default theme); no CDN.

## State

- Pull request #1 is merged (2026-10-13): `main` holds the Flowbite submodule, `CLAUDE.md`, the dev
  team in `.claude/` and the project skills.
- Git identity for this repo is `Maanas Royy <m4manas@gmail.com>` (local config, there is no
  global email). The fork's commits were recreated with it on 2026-10-13, so `main` was force
  pushed once by maanas.
- Branch `fix/clean-clone-start` is pull request #2 (2026-10-13,
  https://github.com/maanas/FastAPI-HTMX/pull/2, waiting for maanas): the
  starter installs with `uv sync`, builds its database with `alembic upgrade head`, starts, and
  passes `pytest -q app/tests` (15 tests). Every direct dependency is at its latest release and
  pinned with `==`. Login, registration and the authenticated pages were exercised in-process
  (TestClient) on the upgraded stack, not in a browser.
- Workers get their settings as environment variables, never a `.env` file: the ten names are in
  `.env.example`.
- Two retro proposals wait for the owner in `.claude/learning/proposals/` (checker: no `ls` of
  `.env`, no `timeout`; coder: stop a server by PID, never `pkill` by name).
- Next: "Assets off the CDNs" on a branch stacked on `fix/clean-clone-start` (the owner agreed to
  stacking on 2026-10-13).

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
- [x] **Make it start from a clean clone** (2026-10-13, branch `fix/clean-clone-start`): uv with a
  lock file, all dependencies upgraded and pinned, the initial migration `0001_initial_schema` with
  named constraints, the test suite collecting and passing, `.env.example`, and the README for the
  uv flow with `AUTH_SECRET`. Left open by it, listed below: sqlalchemy 2.1, the `Permission`
  type, the login cookie on http, `setup.ps1`.
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
  Found in the review of the upgrade (2026-10-13), both older than it: `verify_jwt` in
  `app/database/security.py:110` calls the async `on_decode_jwt` without `await`, so the payload is
  always truthy and any cookie value passes that check; `app/routes/view/upload.py:43` awaits the
  non-async `handle_error`, a TypeError on the upload error path.
  The login cookie (`CookieTransport` in `app/database/security.py`) is always `Secure`, whatever
  `COOKIE_SECURE` says: login over plain http on 127.0.0.1 may fail in some browsers. Not tried.
- [ ] **Housekeeping**: static and template paths relative to the package (today relative to the
  working directory), a LICENSE file (the README says MIT, the repo has none: ask upstream or
  state it for our changes), the 49 existing ruff findings, sqlalchemy 2.1 once
  fastapi-users-db-sqlalchemy allows it (held at 2.0.54), `setup.ps1` and the Windows path
  in the README (`setup.ps1` still calls poetry and the old migration flow), `@app.on_event` to a
  lifespan handler, more tests (15 today; they create missing tables in the `DATABASE_URL`
  database, so they want a throwaway database or a fixture that refuses a real one).
- [ ] **`Permission` type** (`app/models/groups.py`): it subclasses `sqlalchemy.Enum` with no
  values, so `group.permission` is an unconstrained string and would fail on Postgres as a native
  enum. Make it a Python `enum.Enum` or a plain string, with its own migration (`0002_...`).
- [ ] **Decide what medusa takes**: the folder pattern (`routes/view`, `routes/api`,
  `templates/{base,pages,partials}`), the shell and the asset build; users, roles, groups, MinIO
  and CSRF only when medusa gets its first write action (its login may be Tailscale identity).
- [ ] **Background jobs** (owner's idea, 2026-10-13): a Postgres job queue in this stack. Decide
  after the starter runs on Postgres (SQLite only today); candidates to compare then are a
  `SELECT ... FOR UPDATE SKIP LOCKED` table and a library such as procrastinate or pgqueuer.
