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

- Pull requests #1 to #10 are merged (#10 on 2026-10-14). `main` holds the uv setup with pinned
  dependencies, the vendored assets, the CSS build, the whole template task (every template is
  Flowbite 4.0.2 markup, 3,592 lines down to 1,387), hyperscript removed, the Alpine CSP build,
  the security task and the browser pass. The suite has 427 tests there, 584 with
  `feat/htmx-leftovers`.
- Git identity for this repo is `Maanas Royy <m4manas@gmail.com>` (local config, there is no
  global email). The fork's commits were recreated with it on 2026-10-13, so `main` was force
  pushed once by maanas.
- Versions checked on 2026-10-13: every pinned package and vendored file is at its latest release
  (Flowbite 4.0.2, Alpine 3.17.4, htmx 2.0.11, Tailwind CLI 4.3.3, Inter 5.3.0, all direct Python
  dependencies), except sqlalchemy (held at 2.0.54 by fastapi-users-db-sqlalchemy).
- The app was clicked through in Chrome on 2026-10-13 (see "Browser pass"): the console stayed
  clean on every page. Upload, download and delete ran against a real MinIO server on 2026-10-14
  (see "MinIO pass").
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
- Two more were applied with the Browser pass task on 2026-10-14 (checker: wait for `/login`,
  save the CSRF cookie from `GET /login`, placeholder settings instead of SKIPPED;
  `htmx-patterns`: the browser pass method in `reference/browser-pass.md`).
- The "htmx leftovers" task (2026-10-14, branch `feat/htmx-leftovers`) also rewrote the README
  and replaced the logo (`app/static/img/logo/logo.svg`). The demo GIF section is gone from the
  README and its file is deleted (it showed the old interface): record a new one when wanted.
  The ER diagram was not checked against the models.
- Six retro proposals were applied with the "htmx leftovers" task on 2026-10-14 (checker:
  placeholder settings by default, zsh special variable names; coder: no exception object to
  loguru in a request path, ruff after every fix round, keep the guarantee of a test it rewrites;
  `htmx-patterns`: the error answers, CSRF helper and exception handler as shipped, and the
  expected htmx console line in a browser pass; `new-page`: title block, `path_for`,
  `submitted_form`).
- One retro proposal was applied with the "MinIO pass" task on 2026-10-14 (checker: run
  `alembic upgrade head` on the scratch database before creating the superuser).
- Three retro proposals were applied with the "Housekeeping" task on 2026-10-14 (checker: never
  test whether `.env` exists, every placeholder setting named, the CSRF token in the
  `X-CSRF-Token` header for write routes; `commit`: message style from `git log main`).
- One retro proposal was applied with the "`Permission` type" task on 2026-10-14 (checker: the
  placeholder settings rule stated at the pytest step too).
- A local MinIO server for a test: `minio/minio` is gone from Docker Hub and `quay.io/minio/minio`
  refuses anonymous pulls (both checked 2026-10-14); `cgr.dev/chainguard/minio:latest` works, the
  command is in the README. The image is still on the Mac Pro, the container is removed.
- Pull requests #11 to #14 are merged (2026-10-14). "`Permission` type" is on
  `fix/permission-type`.
- Next: decide what medusa takes.

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
- [x] **htmx leftovers** (2026-10-14, branch `feat/htmx-leftovers`), found in the htmx 2 audit and
  the browser pass. Checked in Chrome at the end (scratch database): no CSP violation, "CSP Parser
  Error" or "Undefined variable".
  - Templates render paths, not absolute URLs: the Jinja global `path_for` (`app/templates.py`)
    replaces `url_for`, which `template_rules.py` now refuses, so htmx's `selfRequestsOnly` holds
    behind a proxy that changes scheme or host.
  - `csrf_token_for` (`app/routes/view/csrf.py`) issues every CSRF token and reuses the token of
    a valid cookie with more than half its lifetime left: a form opened by URL saves, and a
    second tab no longer breaks the first. Write routes no longer replace the cookie. A
    successful login sets a new pair (`rotate_csrf_cookie` in `on_after_login`).
  - `handle_error` answers with a status (422 invalid form, the app's own 403, 404, 409, 403 with
    a fixed message for a failed CSRF check, 500 with a fixed message for anything else) and the
    header `X-Error-Rendered`; a listener in `shell.js` lets htmx swap only those answers. The
    log gets type and stack frames, never variable values, SQL or parameters. A refused delete
    keeps the list and shows an alert (`alert_error`). Write forms push no URL.
  - A failed form comes back with the typed values (`submitted_form`), also after a failed CSRF
    check. The user edit error path no longer reads the stored profile for a normal user.
  - A fragment answer starts with the page's `<title>` (`base/fragment.html`), so the tab title
    follows htmx navigation. An unknown URL gets `pages/not_found.html` (as a fragment only for
    `HX-Target: dashboard-body`), JSON for API callers. `http_exception_handler` keeps status
    and detail; a 401 redirects a browser and sends `HX-Redirect` to htmx.
  Left open by it:
  - `path_for` drops a `root_path` prefix: matters only if the app is served under a path.
  - `csrf.py` reads three private attributes of fastapi-csrf-protect 1.0.7 (no public getters);
    the helper tests fail if an upgrade renames them. The CSRF cookie is not removed on log out
    (fastapi-users has no hook with the response); the next login replaces it.
  - An error the app did not render (a crash outside `handle_error`, a network failure) still
    shows the user nothing: a generic toast on `htmx:responseError` and `htmx:sendError`.
  - loguru runs with its default sink (`diagnose=True`): any other logged traceback prints local
    variable values. Configure it once without them. The message of a non-database exception is
    still logged by `handle_error`.
  - `partials/user/add_user.html` and `/get_create_users` are still the broken role form: no CSRF
    token in its markup, `hx-push-url` on a write form (skipped by the guard with a comment).
  - `/dashboard` answers the whole document to an HTMX request (it is a plain link today). The
    not-found page has no navigation, also for a logged-in user.
  - htmx logs "Response Status Error Code 4xx" to the console for every swapped error answer;
    that is expected and not a failure in a browser pass. A successful delete alert uses the
    same danger colours as an error alert.
  - The scripts (`shell.js`, `components.js`) are covered by string guards and the browser pass
    only: there is no JS test runner.
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
  submit before htmx fires `htmx:validation:validate`. Confirmed in the browser pass and
  dropped there, with the `requiredMessage` component.
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
  - The local `users.db` holds no user (checked 2026-10-13), so the old default superuser is
    gone. It was made by the test fixture's `create_all` and has no `alembic_version` table:
    delete it and run `alembic upgrade head` before starting the app. The fixture writes to the
    configured database; a separate test database would stop that (done in "Housekeeping").
  - `setup.ps1` now generates a random secret; that edit was never run (no PowerShell here).
  - The `/users` API router is used by no template or script. Decide whether it stays mounted.
  - The login and register forms showed nothing on a 403 (an expired CSRF cookie): fixed in the
    browser pass, they now show a message for every answer.
  - `http_exception_handler` turned every non-401 `HTTPException` into a bare 400: fixed in
    "htmx leftovers".
  - An unhandled exception answers 500 without the security headers (Starlette answers it outside
    user middleware).
  - `COOKIE_SAMESITE=none` with `COOKIE_SECURE=false` is refused by fastapi-csrf-protect on the
    first CSRF request, not at startup.
  - The first htmx indicator needs the `.htmx-indicator` rules in `app/static/css/src/` (htmx no
    longer injects them). An Alpine `:style` string binding would be blocked by the policy and no
    guard catches it. The eval guard does not see `data-hx-*` attributes or a `js:` value that
    comes from a Jinja expression.
- [x] **Browser pass** (2026-10-13, branch `fix/browser-pass`). Done in
  Chrome through the Claude extension against a started app with `COOKIE_SECURE=false` on
  127.0.0.1 and a scratch database. No CSP violation, "CSP Parser Error" or "Undefined variable"
  on any page. Working: login (email check, wrong password, Enter and Submit), register and its
  messages, logout, the dashboard, the mobile drawer at 520 px, roles, users and groups (add,
  edit, delete with its confirm, the alerts, the user profile popover, user allocation, the
  `revealed` load), a normal user's reduced sidebar and "Not authorized" pages, back, forward and
  reload, `app.css`, the Inter font and the select and checkbox icons. The upload form works up
  to the storage call ("File storage is not available" with no MinIO). The navbar has no user
  dropdown and the forms have no password toggle or radio: nothing to check there.
  Fixed in this task: the user edit Cancel never asked and reloaded the page; the group and role
  edit Cancel reset the form before the confirm was answered; the four custom "required"
  messages never showed (the browser's own check runs first), so they and their Alpine
  components are gone, and the add role form no longer opens with two error messages; login and
  register showed nothing on a 422, a 403 or a network error; the three phone examples in the
  placeholder failed the field's own pattern; the profile alert printed a Python tuple; the
  password help text did not name the required special characters.
  Still open:
  - Upload against a real MinIO server: done in "MinIO pass".
  - `confirm()` dialogs were answered by a stub in the page (the extension cannot see a native
    dialog); htmx called it with the right text each time.
  - Small: every profile field is required to save a role for a user; the upload message
    "'hello' is ready for upload" drops the file extension; the role edit Cancel has no
    confirm while the group and user ones do; the sidebar marks no current page; the "Beta"
    notice returns on every full page load.
  - The findings that belonged to the error handling are fixed in "htmx leftovers".
- [x] **MinIO pass** (2026-10-14, branch `fix/minio-pass`). Done in Chrome against MinIO
  RELEASE.2026-09-22 in a container (Chainguard image), a scratch database and throwaway keys.
  Working: upload, the table refresh, download (the bytes match; attachment, `nosniff`, a name
  with accents, spaces and brackets), delete (row and object both gone), and with the server
  stopped a download and a delete each answer "File storage is not available" after about 6
  seconds and keep the row (an upload with no server was checked on 2026-10-13).
  Fixed in this task: nothing created the bucket, so a new server refused every upload
  (`ensure_bucket` in `app/core/minio_core.py`, called by the upload route before the first
  store, remembered per process after a success); the success alert printed the storage address
  (host, bucket, object name); file delete had no confirm.
  Left open by it:
  - A failed download answers at the `/download/...` URL with the upload heading and the message
    only, no form and no table: the user has to go back.
  - The MinIO client's calls are synchronous inside `async def`: they block the event loop, for
    about 6 seconds per request when the server is down (`asyncio.to_thread`).
  - No test pins that a file refused by validation never reaches the bucket check (one
    `bucket_checks == 0` assert in an existing test).
  - With several worker processes, two first uploads at once can both try to create the bucket;
    the loser answers 503 once.
  - `MinioClient.create_bucket` is unused now. The date column shows `14-10-2026` with no time.
- [x] **Housekeeping** (2026-10-14, branch `chore/housekeeping`): templates, static files, the
  Alembic location and the settings' `.env` resolve from the package, so the app runs from any
  directory (`test_working_directory.py` starts it from another one); `@app.on_event` is a
  lifespan handler. The suite builds its own throwaway SQLite database from the migrations in
  `app/tests/conftest.py` and refuses to run on the `DATABASE_URL` database (605 tests). `uvx ruff
  check .` is at 0 (`.claude` excluded). Form text goes through `clean_text`
  (`app/core/text.py`): tags stripped, stored as typed, escaped once on output; every sink was
  checked (templates, `x-text` alerts, `json.dumps` headers, the download header, the object
  name). `pydantic_partial` keeps the source model's validators; `/post_update_group/{group_id}`
  has its slash; the `print()` is gone; a missing `group_desc` is NULL. `setup.ps1` is rewritten
  for uv; LICENSE is MIT for the fork's changes (owner's decision), the README says the upstream
  code's license is as upstream states it (MIT in its README, no file).
  Left open by it:
  - `setup.ps1` was never run (no PowerShell on the Mac Pro): run it once on Windows.
  - sqlalchemy 2.1: still blocked, fastapi-users-db-sqlalchemy 7.0.0 needs `<2.1.0` (checked
    2026-10-14).
  - A relative SQLite path in `DATABASE_URL` (the `.env.example` default) still follows the
    directory the app starts from.
  - `user.py` builds `role_id` as a one-element tuple (`(nh3.clean(...),)`, about line 255).
  - The conftest error path for a failed `alembic upgrade head` was never triggered in a run.
  - Ask upstream to add the MIT LICENSE their README claims (an issue for maanas to open).
- [x] **`Permission` type** (2026-10-14, branch `fix/permission-type`): `Permission` in
  `app/models/groups.py` is a `str, enum.Enum` (read, write, delete, admin), stored as
  `VARCHAR(16)` with CHECK `ck_group_permission` (no native enum, the same on SQLite and
  Postgres; owner's choice). Migration `0002_permission_enum` sets any other value to NULL, then
  changes the type and adds the check; checked up, down and up on SQLite, `alembic check` clean.
  `app/tests/test_permission.py` proves the check refuses a value after the migrations.
  Left open by it:
  - Nothing reads or writes `group.permission` (no form, schema or route).
  - The migration was not run on Postgres (read only); `alembic upgrade --sql` fails on SQLite
    because batch mode needs a connection.
- [ ] **Decide what medusa takes**: the folder pattern (`routes/view`, `routes/api`,
  `templates/{base,pages,partials}`), the shell and the asset build; users, roles, groups, MinIO
  and CSRF only when medusa gets its first write action (its login may be Tailscale identity).
- [ ] **Background jobs** (owner's idea, 2026-10-13): a Postgres job queue in this stack. Decide
  after the starter runs on Postgres (SQLite only today); candidates to compare then are a
  `SELECT ... FOR UPDATE SKIP LOCKED` table and a library such as procrastinate or pgqueuer.
