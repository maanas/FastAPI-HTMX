---
name: new-page
description: The recipe for adding one page to the starter - view route, page template, partials, router registration, sidebar link and test, in this repo's folder pattern. Use when a step adds a new screen or a new CRUD section, so the pattern is not rediscovered from the existing pages.
---
# New page

## Essentials

A page is five pieces, always in these places:

- Routes: `app/routes/view/<name>.py`, router `<name>_view_route`, registered in `app/app.py`.
- Page: `app/templates/pages/<name>.html`, extends the shell, fills the content block only.
- Partials: `app/templates/partials/<name>/<action>_<name>.html`.
- Sidebar link, in the same markup as its neighbours.
- Test: `app/tests/test_<name>.py`.

Reference: `app/routes/view/role.py`. Reads and writes go through `SQLAlchemyCRUD`. Markup comes
from the `flowbite` skill. No new base template, no per-page `<script>` or `<link>`.

## Contents

| Read | When |
|---|---|
| [Steps](#steps) below | Every new page |
| [reference/route.md](reference/route.md) | Writing the route file: handler signature, CSRF, input cleaning, errors |
| [reference/templates.md](reference/templates.md) | Writing the page and its partials |
| [reference/data.md](reference/data.md) | The page owns a new model or changes one |
| [reference/checklist.md](reference/checklist.md) | Before you report the step as done |

## Steps

1. Route file with one `GET /<name>` for the page and one route per partial.
2. Schema in `app/schema/<name>.py` when the page takes input.
3. Page template, then the partials.
4. `app.include_router(<name>_view_route, tags=["Pages", "<Name>"])` in `app/app.py`.
5. Sidebar link.
6. Test.
7. Run the checklist.
