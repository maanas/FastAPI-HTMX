---
name: flowbite
description: Finds the exact Flowbite v4 markup, theme variables and JS behaviour for a component in the theme/flowbite submodule without loading the whole docs. Use before writing or changing any template markup, picking a colour or radius class, or wiring a modal, drawer, dropdown, tabs or other interactive component.
---
# Flowbite v4 lookup

## Essentials

- Existing Flowbite components only. If no variant fits, stop and report; never build a custom one.
- Find a variant: `grep -n '^## ' theme/flowbite/content/components/<name>.md`, then read only that
  heading's `{{< example >}}` block (about 60 lines).
- Copy the markup as it is. Change text, `id`s, `href`s and field names; keep classes, `data-*` and
  ARIA attributes.
- Keep the semantic classes (`bg-brand`, `text-heading`). No palette class, no arbitrary value.
- Never read `theme/flowbite/llms-full.txt` (2.8 MB). Never edit the submodule.

## Contents

| Read | When |
|---|---|
| [Steps](#steps) below | Every lookup |
| [reference/locations.md](reference/locations.md) | The component is not under `content/components/`, or you do not know its file name |
| [reference/tokens.md](reference/tokens.md) | Choosing or changing a colour, font, radius or dark-mode value |
| [reference/javascript.md](reference/javascript.md) | The component opens, closes or toggles (modal, drawer, dropdown, tabs, tooltip) |

## Steps

1. List the variants: `grep -n '^## ' theme/flowbite/content/components/<name>.md`.
2. Pick the variant that already does the job. Do not combine two variants into a new layout.
3. Read from that heading's line number with a limit of about 60 lines: the markup sits between
   `{{< example ... >}}` and `{{< /example >}}`.
4. Copy it into the template and change only the content.
5. Check that every `id` is unique on the page and that each trigger names its target's `id`.
