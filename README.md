<p align="center">
  <img src="app/static/img/logo/logo.svg" width="96" alt="FastAPI HTMX starter logo">
</p>

<h1 align="center">FastAPI HTMX</h1>

<p align="center">
  A small starter for server-rendered FastAPI sites: Jinja2 templates with HTMX, Alpine.js,
  Tailwind CSS v4 and Flowbite v4, with users, roles, groups and file upload already in place.
</p>

This is a fork of [Hybridhash/FastAPI-HTMX](https://github.com/Hybridhash/FastAPI-HTMX), reworked
into a stable base for our own sites. Open work and its order are in [`TODO.md`](TODO.md).

## What is in it

- Login, register and logout with a cookie session (fastapi-users), and a command that creates the
  first superuser. The app ships no default account.
- Roles, groups and users: list, add, edit and delete pages for a superuser, a reduced sidebar for
  a normal user.
- File upload, download and delete against MinIO, for the owner of the file only.
- One shell (Flowbite navbar and sidebar). An HTMX request gets a partial, a full request gets the
  whole page, from the same route.
- CSRF protection on every write, including login and register.
- A strict content security policy: own origin only, no inline script or style, no `eval`.
- No CDN and no Node: every script, stylesheet and font is a pinned file in the repository.
- An Alembic migration for the whole schema, and a pytest suite that also guards the templates.

## Tech stack

| Part | Version | Note |
| --- | --- | --- |
| [Python](https://www.python.org/) | 3.12 | |
| [FastAPI](https://fastapi.tiangolo.com/) | 0.143.0 | served by [Uvicorn](https://www.uvicorn.org/) 0.54.0 |
| [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0.54 | async, SQLite locally (aiosqlite) |
| [Alembic](https://alembic.sqlalchemy.org/en/latest/) | 1.20.0 | migrations |
| [FastAPI Users](https://fastapi-users.github.io/fastapi-users/) | 15.0.5 | users and the login cookie |
| [fastapi-csrf-protect](https://github.com/aekasitt/fastapi-csrf-protect) | 1.0.7 | CSRF token and cookie |
| [Pydantic](https://docs.pydantic.dev/) | 2.14.1 | schemas and settings |
| [Jinja2](https://palletsprojects.com/p/jinja/) | 3.1.6 | templates, autoescape on |
| [NH3](https://github.com/messense/nh3) | 0.3.7 | sanitises form input |
| [MinIO client](https://github.com/minio/minio-py) | 7.2.20 | file storage |
| [htmx](https://htmx.org/) | 2.0.11 | vendored |
| [Alpine.js](https://alpinejs.dev/) | 3.17.4 | vendored, the CSP build |
| [Flowbite](https://flowbite.com/) | 4.0.2 | vendored JS, markup from its components |
| [Tailwind CSS](https://tailwindcss.com/) | 4.3.3 | standalone CLI, build time only |

Python dependencies are pinned in `pyproject.toml` and locked in `uv.lock`. Vendored files, their
sources and checksums are listed in [`VENDORED.md`](VENDORED.md).

## Setup

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

1. **Clone the repository:**

   ```sh
   git clone https://github.com/maanas/FastAPI-HTMX.git
   cd FastAPI-HTMX
   ```

2. **Install dependencies.** This creates `.venv` from `uv.lock` (runtime and dev tools):

   ```sh
   uv sync
   ```

3. **Create the `.env` file** and edit it. At least replace the `change-me-...` secrets:

   ```sh
   cp .env.example .env
   ```

4. **Create the database** from the committed migration:

   ```sh
   .venv/bin/alembic upgrade head
   ```

   If you have a database that was created before the migration existed, run
   `.venv/bin/alembic stamp 0001_initial_schema` once instead.

5. **Create a superuser** (or promote an existing user):

   ```sh
   .venv/bin/python -m app.commands.create_superuser
   ```

   It reads `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` from the environment and prompts for a
   missing value in a terminal. The password needs at least 12 characters.

6. **Start the application:**

   ```sh
   .venv/bin/python main.py
   ```

   It serves on `http://127.0.0.1:8080`.

7. **Run the tests.** Run them after step 4: they use the database `DATABASE_URL` points to.

   ```sh
   .venv/bin/python -m pytest -q app/tests
   ```

### Environment variables

`.env.example` lists every variable with a placeholder value that works for local development
over http. Copy it to `.env` and edit it. The app does not start without the variables marked
required.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | Database URL, SQLite by default (`sqlite+aiosqlite:///./users.db`) |
| `AUTH_SECRET` | yes | Signs the login token. The app refuses to start if it is missing, a placeholder or shorter than 32 characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `MINIO_URL` | yes | MinIO server URL |
| `MINIO_ACCESS_KEY` | yes | MinIO access key |
| `MINIO_SECRET_KEY` | yes | MinIO secret key |
| `MINIO_BUCKET` | yes | MinIO bucket name |
| `MINIO_SECURE` | no (`false`) | `true` for HTTPS to MinIO. Use it in production |
| `CSRF_SECRET_KEY` | yes | Signs the CSRF token |
| `COOKIE_SAMESITE` | yes | CSRF and login cookie SameSite: lowercase `lax`, `strict` or `none`. `none` needs `COOKIE_SECURE=true` |
| `COOKIE_SECURE` | yes | `false` for local http, `true` in production (HTTPS) |
| `SUPERUSER_EMAIL` | no | Read only by `app.commands.create_superuser` |
| `SUPERUSER_PASSWORD` | no | Read only by `app.commands.create_superuser`, at least 12 characters |

With placeholder MinIO values the app starts and every page works, but an upload answers "File
storage is not available". For file storage, run a MinIO server and set the four `MINIO_*` values.
The app creates the bucket on the first upload if it is missing.

A local server (`minio/minio` is no longer on Docker Hub and `quay.io/minio/minio` refuses
anonymous pulls; this image worked on 2026-10-14):

```bash
docker run -d --name minio -p 127.0.0.1:9000:9000 -e MINIO_ROOT_USER=<access key> \
  -e MINIO_ROOT_PASSWORD=<secret key> cgr.dev/chainguard/minio:latest server /tmp/data
```

Set `MINIO_URL=http://127.0.0.1:9000` and the two keys to the values you chose. The data is lost
with the container.

### Windows

`setup.ps1` is the upstream helper script. It still expects poetry and the old migration flow and
has not been updated for uv: follow the steps above instead.

## Project structure

```
app/
├── app.py                 FastAPI app, routers, static mount
├── exception.py           handlers for HTTP and CSRF errors
├── templates.py           the Jinja2 environment
├── commands/              create_superuser
├── core/                  settings (auth, CSRF, MinIO), security headers
├── database/              engine, session, auth (fastapi-users), init_models
├── migrations/            Alembic
├── models/                SQLAlchemy models: users, groups, upload
├── schema/                Pydantic schemas
├── routes/
│   ├── view/              page and partial routes (HTML)
│   └── api/               JSON routes
├── templates/
│   ├── base/              base.html (shell), auth_base.html (login, register)
│   ├── pages/             thin pages that include a partial
│   └── partials/          the fragments an HTMX request gets
├── static/
│   ├── css/               app.css (built) and src/ (input, tokens, fonts)
│   ├── js/                the app's own scripts
│   ├── vendor/            htmx, Alpine.js, Flowbite, Inter
│   └── img/
└── tests/                 pytest
tools/css.sh               rebuilds app.css
theme/flowbite/            submodule, Flowbite 4.0.2, reference only
main.py                    entry point
```

## How pages work

- Every screen has a page in `templates/pages/` and a fragment in `templates/partials/`. The page
  extends the shell and only includes the fragment. `render_view` in
  `app/routes/view/fragments.py` answers an HTMX request with the fragment and any other request
  with the page.
- Markup is Flowbite v4 components only. `theme/flowbite/content/components/<name>.md` holds the
  markup for each component.
- Templates carry no inline script, no `style` attribute and no `on*=` handler. Behaviour lives in
  named Alpine components in `app/static/js/components.js`, because the Alpine CSP build evaluates
  no free-form JavaScript.
- A write route checks the CSRF pair first: the token travels in the `X-CSRF-Token` header, set by
  `hx-headers` on the form.
- `app/tests/test_templates.py` fails a template that breaks one of these rules or uses a class
  that is missing from the built `app.css`.

## Security

- `AUTH_SECRET` has no default and is never logged. The login cookie is `HttpOnly`; its `Secure`
  and `SameSite` flags follow `COOKIE_SECURE` and `COOKIE_SAMESITE`.
- Every POST of the auth routes (login, register, forgot and reset password, verify, the users API)
  needs the CSRF pair and answers 403 without it. Logout is exempt.
- Every response carries a content security policy that allows the own origin only (no inline
  script or style, no `eval`, no CDN), plus `X-Content-Type-Options`, `Referrer-Policy`,
  `X-Frame-Options`, `Permissions-Policy` and `Cross-Origin-Opener-Policy`. They are listed in
  `app/core/security_headers.py`. `Strict-Transport-Security` is sent only when
  `COOKIE_SECURE=true`.
- htmx runs with `allowEval`, `allowScriptTags` and `includeIndicatorStyles` off and
  `selfRequestsOnly` on (the `htmx-config` meta tag in `base/base.html`).
- The API docs pages (`/docs`, `/redoc`, `/openapi.json`) are off: Swagger UI needs a CDN and an
  inline script, which the policy forbids.
- Uploads are validated before they are stored, limited to 10 MB, and only the owner can download
  or delete a file.

## CSS

The stylesheet `app/static/css/app.css` is built from `app/static/css/src/input.css` (Tailwind v4
with the Flowbite plugin) and the design tokens in `app/static/css/src/tokens.css`, an unchanged
copy of Flowbite's default theme. The built file is committed, so running the app needs no build
step, and Node is not needed to rebuild it:

```bash
tools/css.sh            # rebuild app/static/css/app.css
tools/css.sh --watch    # rebuild on every change
```

The first run downloads the Tailwind standalone CLI into `build/` (not committed) and checks its
sha256 against the value pinned in the script. Rebuild and commit `app.css` after you change a
template, a script in `app/static/js/` or `tokens.css`.

The Inter font is vendored in `app/static/vendor/inter/` and declared in
`app/static/css/src/fonts.css`, so pages load it from this server and never from a CDN.

## Adding a model

A model change ships with its migration and its import in `init_models`.

1. Define the model in `app/models/`.
2. Import it in `init_models` in `app/database/base.py`, so Alembic sees it:

   ```python
   from ..models.financial import Invoice  # noqa: F401
   ```

3. Generate the migration (see `app/migrations/README` for the naming):

   ```bash
   .venv/bin/alembic revision --autogenerate --rev-id 0002_invoice -m "invoice"
   ```

4. Review the generated script, then apply it:

   ```bash
   .venv/bin/alembic upgrade head
   ```

## ER diagram

![ER Diagram](app/static/img/logo/er_diagram.png)

## Known gaps

The starter runs on SQLite only so far. Upload, download and delete were run against a real MinIO
server on 2026-10-14 (RELEASE.2026-09-22); the tests use a fake storage object. Password reset has
no page yet. The full list is in [`TODO.md`](TODO.md).

## Contributing

Open an issue or a pull request on [maanas/FastAPI-HTMX](https://github.com/maanas/FastAPI-HTMX).

## License

The upstream project states the MIT License in its README. The repository holds no `LICENSE` file
yet; adding one is listed in `TODO.md`.
