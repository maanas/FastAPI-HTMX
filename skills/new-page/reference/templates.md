# The page and its partials

## Page: `app/templates/pages/<name>.html`

- `{% extends %}` the shell in `app/templates/base/` and fill its content block only.
- The shell owns `<head>`, the navbar, the sidebar, the CSRF header on `<body>` and every script and
  stylesheet. A page adds none of them.
- The page lays out existing Flowbite components: a heading, a toolbar with the "add" button, the
  list, the modal or drawer that holds the form.

## Partials: `app/templates/partials/<name>/`

| File | Holds |
|---|---|
| `<name>_table.html` | The list; its root has the `id` every write targets |
| `add_<name>.html` | The create form |
| `edit_<name>.html` | The edit form |

- A partial is a fragment: no `extends`, no `<html>`.
- The page includes the list partial with `{% include %}`, so the first render and a later swap use
  the same markup.
- A form posts with `hx-post` on the `<form>` and targets the list's `id`.

## Which Flowbite component

| Part | Component (load with the `flowbite` skill) |
|---|---|
| List | `tables.md`, `pagination.md` |
| Form | `forms/input-field.md`, `forms/select.md`, ... inside `modal.md` or `drawer.md` |
| Feedback | `toast.md` or `alerts.md` |
| Row actions | `dropdowns.md` or `button-group.md` |
| Empty or loading state | `skeleton.md`, `spinner.md` |

## Sidebar link

Add one item to the sidebar partial in `app/templates/partials/`, copying a neighbour's markup
exactly. A superuser-only page sits inside the same condition as the other admin links.

## Do not

- No copy of an existing page as a start: the pages from upstream are old markup, 400 to 550 lines
  each, and are being replaced (see `TODO.md`).
- No behaviour in the template: an Alpine component goes in `app/static/js/` as `Alpine.data(...)`.
- No hard-coded colour, no arbitrary value, no custom layout.
