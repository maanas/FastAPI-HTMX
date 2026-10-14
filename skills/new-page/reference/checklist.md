# Before you report

## Test: `app/tests/test_<name>.py`

- The page answers `200` for a signed-in user, and redirects when signed out.
- With `HX-Request: true` the response is the partial (no `<html`).
- A write without the CSRF token is refused and stores nothing.
- The schema rejects input that is too short, too long or missing.

Detail: the `htmx-patterns` skill, `reference/testing.md`.

## Checks

- [ ] Router registered in `app/app.py`; the page is reachable from the sidebar.
- [ ] Every write handler validates CSRF and has its auth dependency.
- [ ] `grep -nE 'https?://|<script|style=| on[a-z]+=|hx-on' app/templates/pages/<name>.html app/templates/partials/<name>/` prints nothing.
- [ ] No palette class or arbitrary value: `grep -nE '(bg|text|border)-(blue|gray|red|green)-[0-9]|\[#' <same files>` prints nothing.
- [ ] Every `id` in the new templates is unique on the page.
- [ ] A new model has its migration and its `init_models` import.
- [ ] The page defines one literal `{% block title %}<View> | FastAPI HTMX{% endblock %}`; no `<title>` in a partial. Add the view to `VIEWS` in `app/tests/test_titles.py`.
- [ ] URLs in templates use `path_for`, never `url_for`.
- [ ] A failed form re-renders with `form` from `submitted_form`, so typed values stay.
- [ ] `uvx ruff check` on the changed files and `.venv/bin/python -m pytest -q app/tests` pass.

## Report to the director

The pages and tests the checker should run, and a "Review required" line for any change to auth,
CSRF, a migration or the shell.
