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
- Two retro proposals were approved and applied on 2026-10-13 (checker: no `ls` of `.env`, no
  `timeout`; coder: stop a server by PID, never `pkill` by name). The owner also approved the
  security, htmx and other items in the change list below as work to do.
- Branch `feat/vendor-assets` is pull request #3 (https://github.com/maanas/FastAPI-HTMX/pull/3),
  stacked on `fix/clean-clone-start`: merge #2 first (2026-10-13). No template loads
  from a CDN any more. Flowbite JS 4.0.2, Alpine 3.17.4 and htmx 2.0.11 are vendored under
  `app/static/vendor/` and listed in `VENDORED.md`, each verified against the npm registry
  checksum. Nothing was opened in a browser: Flowbite JS 4.0.2 against the 1.x markup, Alpine
  3.17.4 and htmx 2 client behaviour are unverified. Open the pages once before relying on it.
- Branch `feat/css-build` (2026-10-13) is stacked on `feat/vendor-assets`: merge #2, then #3, then
  its pull request. The stylesheet is now `app/static/css/app.css`, built by `tools/css.sh` with
  the Tailwind 4.3.3 standalone CLI (no Node). Not opened in a browser: the old Flowbite 1.x
  markup on a Tailwind v4 stylesheet will look different in places until the templates are redone.
- This Mac has no `.env` for the repo: workers run the tests with the ten settings exported and a
  throwaway SQLite file, so tell the checker not to report the missing `.env`.
  One retro proposal waits for the owner in `.claude/learning/proposals/`
  (`2026-10-13-checker-env-vars-ok`: the checker uses exported settings instead of stopping on a
  missing `.env`).
- Next: "Templates to Flowbite v4 markup".

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
- [x] **Assets off the CDNs** (2026-10-13, branch `feat/vendor-assets`): Flowbite JS 4.0.2, Alpine
  3.17.4 and htmx 2.0.11 vendored from the npm registry tarballs with curl (no Node), listed in
  `VENDORED.md`. Two files are vendored only until their own item replaces them: the Flowbite
  1.8.1 stylesheet ("CSS build"; it holds three unused S3 image URLs) and hyperscript 0.9.11
  ("Hyperscript out"). htmx 2 sends DELETE parameters in the URL: the group and file delete routes
  now read the query string.
- [ ] **htmx leftovers** found in the htmx 2 audit (2026-10-13), all older than it:
  - `delete_file` in `app/routes/view/upload.py` has no CSRF check (the group and role deletes do).
  - `hx-vals` in `app/templates/pages/groups.html:214` and `partials/upload/files_table.html` is
    JSON built by string interpolation: a quote in a name breaks it. Use `hx-vals` from a
    `tojson` filter or a path parameter.
  - `hx-ext="response-targets"` (`user.html:88`, `groups.html:96`, `role.html:124`) and
    `hx-target-404` (`groups.html:104`, `role.html:132`) need an extension that was never loaded:
    vendor it or remove the attributes.
  - `hx-get` and `hx-post` use absolute URLs from `url_for`. htmx 2 refuses a request whose
    origin differs from the page (`selfRequestsOnly`), so behind a proxy that changes scheme or
    host nothing is sent: run uvicorn with proxy headers or render relative URLs.
  - `hx-on::after-request` in `pages/upload.html:144` needs eval, and `user.html:293` deletes
    with an `onclick` handler: both go when the strict content security policy comes.
  - `handle_error` (`app/routes/view/errors.py`) answers 200 with an error body for every
    failure, including a missing CSRF header: a rejected request should be a 4xx.
- [x] **CSS build** (2026-10-13, branch `feat/css-build`): `tools/css.sh` downloads the Tailwind
  4.3.3 standalone CLI into the ignored `build/tailwind/`, checks its pinned sha256 and builds
  `app/static/css/app.css` (committed, 47 KB) from `app/static/css/src/input.css`. The one tokens
  file is `app/static/css/src/tokens.css`, an unchanged copy of Flowbite 4.0.2's default theme.
  Flowbite's Tailwind plugin loads from the submodule without Node: its only outside dependency,
  `mini-svg-data-uri` 1.4.4, is vendored at `theme/node_modules/`. The Flowbite 1.8.1 stylesheet
  is gone. Rebuild after any template or script change that adds a class.
  Open: the default theme names the Inter font, which Flowbite loads from Google Fonts. It is not
  loaded here (no CDN), so pages use the system font: vendor Inter or choose another font.
- [ ] **Templates to Flowbite v4 markup** (about 3,600 lines in `app/templates/`), `base.html` is an
  empty file: make it the generic shell (Flowbite navbar + sidebar). Found in the CSS build:
  17 class names in the templates produce no CSS (12 typos with a dash for the colon such as
  `hover-bg-blue-800` and `sm-w-auto`, `dark:shadow-sm-light` from Flowbite 1.x, and non-classes
  such as `my-scroll`); inline scripts in `pages/user.html:527` and
  `partials/auth_navigation.html:369` and `:378`; `pages/upload.html:443` loads
  `static/js/upload.js` without the leading slash. The static assets test only catches `http(s)://`
  URLs, not protocol-relative `//host` ones.
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
