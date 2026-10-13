# Theme variables and classes

The whole design system sits in one tokens file in the app (see `TODO.md`, "CSS build"). It starts
from Flowbite's default theme, `theme/flowbite/src/themes/default.css`: an `@theme { ... }` block
with the light values, then a `.dark { ... }` block that overrides them.

## Rules

- A new colour, font or radius is a change to the tokens file, never to a template.
- Templates use the semantic class a variable creates. Never a palette class (`bg-blue-700`), never
  an arbitrary value (`bg-[#1a56db]`, `rounded-[10px]`).
- Colours are not decided yet: keep the default theme's values until the owner chooses.

## How a variable becomes a class

`--color-<name>` in `@theme` gives `bg-<name>`, `text-<name>`, `border-<name>`. Examples from the
default theme:

| Variable | Class | Meaning |
|---|---|---|
| `--color-brand`, `-soft`, `-softer`, `-medium`, `-strong` | `bg-brand`, `bg-brand-softer` | Brand surfaces |
| `--color-fg-brand`, `-strong`, `-subtle` | `text-fg-brand-strong` | Brand text |
| `--color-neutral-primary`, `-soft`, `-medium`, `-strong` | `bg-neutral-primary-soft` | Page and card surfaces |
| `--color-heading`, `--color-body`, `--color-body-subtle` | `text-heading`, `text-body` | Text |
| `--color-success*`, `--color-danger*`, `--color-warning*` | `bg-danger-soft`, `text-fg-danger-strong` | Status |
| `--radius-xs`, `-sm`, `--radius`, `-base`, `-lg` | `rounded-base` | Radius |
| `--font-sans`, `--font-body`, `--font-mono` | `font-body` | Fonts |

To find a variable: `grep -n -- '--color-brand' theme/flowbite/src/themes/default.css`.
The naming scheme (`{level}-{accent}`) is explained at the top of
`theme/flowbite/content/customize/variables.md`; read its first 60 lines only.

## Dark mode

Dark values live in the `.dark` block of the same variables, so a template needs no `dark:` class
for a semantic colour. `content/customize/dark-mode.md` covers the toggle.
