# TODO

Fork of Hybridhash/FastAPI-HTMX (`upstream`), kept at `github.com/maanas/FastAPI-HTMX` (`origin`,
SSH as `maanas`; the `gh` CLI on the Mac Pro is logged in as `kkuvam` and cannot open PRs here).
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
- Nothing else is changed. The app has not been run here yet.

## Change list

- [ ] **Run it as it is** first (README setup, `.env`, SQLite) and note what breaks.
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
  defaults it to `my_default_secret_key`: remove the log, refuse to start on the default. Add
  security headers with a strict content security policy (own origin only, no inline script).
  htmx: `allowEval=false`, `includeIndicatorStyles=false`, `selfRequestsOnly=true`.
- [ ] **Housekeeping**: static and template paths relative to the package (today relative to the
  working directory), a LICENSE file (the README says MIT, the repo has none: ask upstream or
  state it for our changes), ruff and pytest brought up to date, `setup.ps1` and the Windows path
  in the README, tests (3 files today).
- [ ] **Decide what medusa takes**: the folder pattern (`routes/view`, `routes/api`,
  `templates/{base,pages,partials}`), the shell and the asset build; users, roles, groups, MinIO
  and CSRF only when medusa gets its first write action (its login may be Tailscale identity).
