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

- Pull requests #1 to #8 are merged (2026-10-13). `main` holds the uv setup with pinned
  dependencies, the vendored assets, the CSS build, the whole template task (every template is
  Flowbite 4.0.2 markup, 3,592 lines down to 1,387), hyperscript removed and the Alpine CSP build.
  The suite has 324 tests there, 415 with `feat/security`.
- Git identity for this repo is `Maanas Royy <m4manas@gmail.com>` (local config, there is no
  global email). The fork's commits were recreated with it on 2026-10-13, so `main` was force
  pushed once by maanas.
- Versions checked on 2026-10-13: every pinned package and vendored file is at its latest release
  (Flowbite 4.0.2, Alpine 3.17.4, htmx 2.0.11, Tailwind CLI 4.3.3, Inter 5.3.0, all direct Python
  dependencies), except sqlalchemy (held at 2.0.54 by fastapi-users-db-sqlalchemy).
- Nothing has been opened in a browser yet (see "Browser pass"). Requests against a started app
  and the tests cover the pages, not the clicks. No upload, download or delete has run
  against a real MinIO server (tests use a fake storage object).
- Workers get their settings as environment variables, never a `.env` file: the ten names are in
  `.env.example`. This Mac has no `.env` for the repo. Workers must never run a bare `export`,
  `env`, `set` or `printenv`: one did on 2026-10-13 and printed the shell environment, with an API
  key in it, into its transcript (rotate that key).
- Three retro proposals were approved and applied on 2026-10-13 (checker: no `ls` of `.env`, no
  `timeout`; coder: stop a server by PID, never `pkill` by name; checker: exported settings
  instead of stopping on a missing `.env`).
- Six more were applied with the Security task (checker: smoke login recipe on port 8091 with a
  superuser from the command, settings in zsh arrays; coder: a template guard needs a must-flag
  and a must-not-flag case; reviewer: runs the tests with placeholder settings when the prompt
  gives none; `htmx-patterns`: a router-wide guard needs a request per existing caller, and the
  shipped headers, both in `reference/security.md`).
- Next: the "Browser pass" item, then "htmx leftovers".

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
  `VENDORED.md`. Two files were vendored only until their own item replaced them, and both are
  gone: the Flowbite 1.8.1 stylesheet ("CSS build") and hyperscript 0.9.11 ("Hyperscript out").
  htmx 2 sends DELETE parameters in the URL: the group and file delete routes
  now read the query string.
- [ ] **htmx leftovers** found in the htmx 2 audit (2026-10-13). Closed by the template task: the
  missing CSRF check on `delete_file`, the string-built `hx-vals`, the `response-targets`
  attributes, `hx-on::after-request` and the `onclick` delete. Still open:
  - `hx-get` and `hx-post` use absolute URLs from `url_for`. htmx 2 refuses a request whose
    origin differs from the page (`selfRequestsOnly`), so behind a proxy that changes scheme or
    host nothing is sent: run uvicorn with proxy headers or render relative URLs.
  - `handle_error` (`app/routes/view/errors.py`) answers 200 with an error body for every
    failure, including a missing CSRF header and "Not authorized": a rejected request should be a
    4xx (then htmx needs to be told to swap those responses). It also shows the raw exception
    text to the user, for example "An unexpected error occurred: The CSRF signatures submitted do
    not match." or SQL from a database error.
  - An add or edit form opened directly by URL (not from its list) renders with an empty CSRF
    token, because the route copies the token from the request header: saving is refused. The
    routes should issue a token themselves.
  - The CSRF cookie is replaced by every page that issues a token, so a second tab makes the
    first tab's next write fail until it is reloaded.
- [x] **CSS build** (2026-10-13, branch `feat/css-build`): `tools/css.sh` downloads the Tailwind
  4.3.3 standalone CLI into the ignored `build/tailwind/`, checks its pinned sha256 and builds
  `app/static/css/app.css` (committed, 47 KB) from `app/static/css/src/input.css`. The one tokens
  file is `app/static/css/src/tokens.css`, an unchanged copy of Flowbite 4.0.2's default theme.
  Flowbite's Tailwind plugin loads from the submodule without Node: its only outside dependency,
  `mini-svg-data-uri` 1.4.4, is vendored at `theme/node_modules/`. The Flowbite 1.8.1 stylesheet
  is gone. Rebuild after any template or script change that adds a class.
  The Inter font the default theme names is vendored too (`@fontsource-variable/inter` 5.3.0,
  OFL-1.1, latin and latin-ext, in `app/static/vendor/inter/`, declared in
  `app/static/css/src/fonts.css`). When the content security policy comes, `font-src` needs
  `'self'`.
- [x] **Templates to Flowbite v4 markup** (2026-10-13, pull request #5 and branch
  `feat/templates-flowbite-v4`): `base/base.html` is the shell (Flowbite navbar and sidebar in
  `partials/shell/`), `base/auth_base.html` leaves the navigation off login and register, and
  every page is a thin template that includes a fragment. `app/routes/view/fragments.py`
  (`render_view`) gives an HTMX request the fragment and a full request the page, with
  `Vary: HX-Request`. No inline script, `style`, `on*=` or `hx-on` is left; `upload.js` loads from
  the shell. `app/tests/test_templates.py` guards all of it per template, including that every
  class used exists in the built `app.css` (the 17 dead class names are gone), and
  `test_static_assets.py` catches `//host` URLs and a stale `app.css`.
  Fixed on the way, each with tests: Jinja autoescape was off (stored XSS through any name);
  upload and file delete had no CSRF check; user delete went around CSRF; group and upload routes
  read data before the CSRF and superuser checks; duplicate role and group names, an unknown user
  id in a group, and every upload delete error answered 500; delete messages trusted client input;
  `handle_error` logged the CSRF token; uploads were stored before validation with no size limit,
  and any superuser could delete or download any file by name (now the owner only).
  Left open by it, listed in the items below or here:
  - Guard gaps no template triggers today: a Jinja block glued to an attribute name hides it from
    `template_rules.py`; classes in a JS template literal or an `x-transition` attribute are not
    checked; the stale-CSS test is skipped where the Tailwind binary is not downloaded (a fresh
    clone, CI) and its binary lookup matches any architecture.
  - Kept as found: register's "Return to login" button requests the dashboard route; "Forgot
    Username/Password" has no `href`; the register success message shows in the error box; the
    login and register cards are not vertically centred (no Flowbite example for it).
  - Rendered by no reachable route: `pages/index.html`, and `pages/user_add.html` with
    `partials/user/add_user.html`, which is a role form that posts to the role route.
  - Upload: if the refresh after a committed insert fails, the cleanup removes the object and the
    row stays; nothing caps the request body except the `Content-Length` check (cap it at the
    proxy); an upload takes about 6 seconds to fail when MinIO is down (client retries).
- [x] **Hyperscript out** (2026-10-13, branch `feat/hyperscript-out`): the four inputs that used
  it (`partials/group/add_group.html`, `edit_group.html`, `partials/role/edit_role.html`,
  `partials/user/add_user.html`) now use one Alpine component, `requiredMessage` in
  `app/static/js/components.js`, with the message in `data-required-message`. The library, its
  script tag and its `VENDORED.md` row are gone, and `test_templates.py` fails if any of it
  returns. Checked by reading the vendored Alpine and htmx source, not in a browser.
  Left open by it: the custom message ("Please enter the Group Type") probably never shows for an
  empty field, before or after this change, because the browser's own `required` check stops the
  submit before htmx fires `htmx:validation:validate`. Either drop the four custom messages or
  make them work (decide in the browser pass).
- [x] **Alpine CSP build** (2026-10-13, branch `feat/alpine-csp`): the shell loads
  `@alpinejs/csp` 3.17.4 (`app/static/vendor/alpinejs/alpine-csp.min.js`) and the standard build
  is gone, so the content security policy needs no `unsafe-eval`. Every `x-data` names a component
  in `app/static/js/components.js` (new: `listAlerts`, `uploadPage`, `roleForm`, `resetForm`,
  `cancelEdit`); the `x-init` watchers moved into `init()`, the login CSRF token arrives through
  `data-csrf-token` and the cancel URL in `edit_user.html` through `data-list-url`.
  `alpine_csp_problems` in `app/tests/template_rules.py` fails a template whose Alpine attribute
  the CSP parser would reject, and a test checks every vendored script's sha256 against
  `VENDORED.md`. The parser in 3.17.4 takes one expression per attribute (operators, ternary,
  object literal and assignment are fine; no arrow function, template literal, second statement,
  comma operator, `window` or `document`, `x-html`). An unknown name in an attribute throws.
  Checked by parsing all 98 template expressions with the package's own parser and by reading its
  evaluator, not in a browser.
  Left open by it: the browser pass (watch the console for "CSP Parser Error" and "Undefined
  variable" on login, register, the three lists, add role and upload; click both Cancel buttons);
  `skills/htmx-patterns/reference/flowbite-alpine.md` says the CSP build takes a property name or
  a method call only, which is stricter than 3.17.4 is (change it through a proposal or keep it
  as the house rule); the guard does not see a `{% if %}` block inside an Alpine attribute value.
- [x] **Security** (2026-10-13, branch `feat/security`): `AUTH_SECRET` is required (32 characters or
  more, no default, never logged; `app/core/auth_settings.py`). Startup creates no superuser:
  `.venv/bin/python -m app.commands.create_superuser` creates or promotes one from
  `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` or a prompt. The login cookie on `/` is really verified
  (`verify_jwt` let any value pass), and its `Secure` and `SameSite` flags follow `COOKIE_SECURE`
  and `COOKIE_SAMESITE` (lowercase `lax`, `strict` or `none` only). Every POST of the fastapi-users
  routers (login, register, forgot and reset password, verify, the users API) needs the CSRF pair
  and answers 403 without it (`require_csrf` in `app/database/security.py`); logout is exempt,
  because the shell's logout button has no token. `DELETE /users/{own id}` answers 400.
  `app/core/security_headers.py` sends the headers on every response: a content security policy
  of own origin only (plus `data:` images for three form icons in `app.css`), no inline script or
  style, no eval; HSTS only when `COOKIE_SECURE=true`. htmx runs with `allowEval`,
  `allowScriptTags` and `includeIndicatorStyles` off. `/docs`, `/redoc` and `/openapi.json` are
  off (Swagger UI needs a CDN and an inline script). The `await handle_error` bug in the upload
  route was already gone. Checked with curl against a started app and by reading the vendored
  scripts, not in a browser.
  Left open by it:
  - A database made before this change still holds `superuser@admin.com` / `password123`: delete
    that user or change its password.
  - `setup.ps1` now generates a random secret; that edit was never run (no PowerShell here).
  - The `/users` API router is used by no template or script. Decide whether it stays mounted.
  - The login and register forms show nothing on a 403 (an expired CSRF cookie); they handle only
    success and 400.
  - `http_exception_handler` (`app/exception.py`) turns every non-401 `HTTPException` into a bare
    400, including the library's 403 and 404.
  - An unhandled exception answers 500 without the security headers (Starlette answers it outside
    user middleware).
  - `COOKIE_SAMESITE=none` with `COOKIE_SECURE=false` is refused by fastapi-csrf-protect on the
    first CSRF request, not at startup.
  - The first htmx indicator needs the `.htmx-indicator` rules in `app/static/css/src/` (htmx no
    longer injects them). An Alpine `:style` string binding would be blocked by the policy and no
    guard catches it. The eval guard does not see `data-hx-*` attributes or a `js:` value that
    comes from a Jinja expression.
- [ ] **Browser pass** (never done; the content security policy makes it more important). With
  the console open, watch for CSP violations, "CSP Parser Error" and "Undefined variable" on:
  `/login` and `/register` (password toggle, error messages, a real login and register);
  `/dashboard` (navbar user dropdown, mobile sidebar drawer, logout); roles, users and groups (add,
  edit, delete with its confirm, both Cancel buttons, the alerts, the `revealed` load of the
  groups list); `/uploads` (upload, table refresh, download, delete, against a real MinIO). Check
  that `app.css` and the Inter font load and the select, checkbox and radio icons show. Login over
  plain http on 127.0.0.1 with `COOKIE_SECURE=false`. Decide the four custom "required" messages
  (see "Hyperscript out").
- [ ] **Housekeeping**: static and template paths relative to the package (today relative to the
  working directory), a LICENSE file (the README says MIT, the repo has none: ask upstream or
  state it for our changes), the 49 existing ruff findings, sqlalchemy 2.1 once
  fastapi-users-db-sqlalchemy allows it (held at 2.0.54), `setup.ps1` and the Windows path
  in the README (`setup.ps1` still calls poetry and the old migration flow), `@app.on_event` to a
  lifespan handler, a fixture that refuses to run the tests against a real database (255 tests
  today; they create missing tables in the `DATABASE_URL` database).
  From the template task: `pydantic_partial` in `app/schema/pydantic_base.py` drops model
  validators, so `FileBase.validate_file_size` never runs (the upload route enforces 10 MB
  itself); `nh3.clean` stores `&` as `&amp;`, which autoescape then shows doubled; the route path
  `/post_update_group{group_id}` has no slash; `print()` in `group.py:536` and `console.log` in
  `components.js:151`; a missing `group_desc` is stored as the text "None".
- [ ] **`Permission` type** (`app/models/groups.py`): it subclasses `sqlalchemy.Enum` with no
  values, so `group.permission` is an unconstrained string and would fail on Postgres as a native
  enum. Make it a Python `enum.Enum` or a plain string, with its own migration (`0002_...`).
- [ ] **Decide what medusa takes**: the folder pattern (`routes/view`, `routes/api`,
  `templates/{base,pages,partials}`), the shell and the asset build; users, roles, groups, MinIO
  and CSRF only when medusa gets its first write action (its login may be Tailscale identity).
- [ ] **Background jobs** (owner's idea, 2026-10-13): a Postgres job queue in this stack. Decide
  after the starter runs on Postgres (SQLite only today); candidates to compare then are a
  `SELECT ... FOR UPDATE SKIP LOCKED` table and a library such as procrastinate or pgqueuer.
