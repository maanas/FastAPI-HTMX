# Where things are in `theme/flowbite/` (v4.0.2)

| Need | Path |
|---|---|
| Component markup, 44 files | `content/components/<name>.md` |
| Form controls | `content/forms/<name>.md` |
| Typography | `content/typography/<name>.md` |
| Charts, datatables, datepicker, WYSIWYG | `content/plugins/<name>.md` |
| Theme variables explained | `content/customize/variables.md`, `theming.md`, `colors.md`, `dark-mode.md` |
| Default theme values | `src/themes/default.css` |
| App shell example (navbar + sidebar) | `layouts/dashboard.html` |
| JS init and instance API | `content/getting-started/javascript.md` |

## File names

`ls theme/flowbite/content/components` lists them. Names that are easy to get wrong:

- Plural: `alerts.md`, `buttons.md`, `dropdowns.md`, `tooltips.md`, `tables.md`, `tabs.md`, `indicators.md`.
- Singular: `modal.md`, `drawer.md`, `navbar.md`, `sidebar.md`, `card.md`, `toast.md`, `badge.md`.
- Forms: `input-field.md`, `select.md`, `checkbox.md`, `radio.md`, `toggle.md`, `textarea.md`,
  `file-input.md`, `search-input.md`, `floating-label.md`, `number-input.md`, `range.md`.

## Which component for which job

| Job | Component |
|---|---|
| App shell | `navbar.md` + `sidebar.md`, as combined in `layouts/dashboard.html` |
| List of records | `tables.md`, with `pagination.md` |
| Create or edit form | `forms/*` inside `modal.md` or `drawer.md` |
| Feedback after an action | `toast.md` or `alerts.md` |
| Row actions | `dropdowns.md` or `button-group.md` |
| Loading state | `spinner.md` or `skeleton.md` |
| Status label | `badge.md` |

## Size

One variant is 20 to 60 lines. A component file is 3 KB to 33 KB: do not read one whole.
`llms-full.txt` is 2.8 MB and is never read; `llms.txt` is only a list of web links.
