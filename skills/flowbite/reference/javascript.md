# Interactive components

Modal, drawer, dropdown, tabs, tooltip, popover, accordion, carousel and collapse are driven by
`data-*` attributes; Flowbite's script binds them once, when the page loads.

## Wiring

- The trigger names the target's `id`: `data-modal-target` + `data-modal-toggle`,
  `data-drawer-target` + `data-drawer-show`, `data-dropdown-toggle`, `data-tabs-target`,
  `data-tooltip-target`, `data-collapse-toggle`. Copy the pair from the variant; do not invent one.
- Keep the ARIA attributes of the variant (`aria-controls`, `aria-expanded`, `aria-hidden`,
  `role="dialog"`).
- `id`s are unique per page. A component rendered once per table row needs the row's id in its
  `id` and in the trigger.

## Options

Each component file has a `## JavaScript behaviour` section (options, methods, example). Read it
only when the default behaviour is not enough:
`grep -n '^## JavaScript behaviour\|^### ' theme/flowbite/content/components/<name>.md`.
Options that exist as `data-*` attributes are set in the markup, not in JS.

## After an HTMX swap

Markup that arrives in a swap is not bound. It is initialised again by one shared listener in
`app/static/js/`, never by a script in the partial. See the `htmx-patterns` skill,
`reference/flowbite-alpine.md`.

## Not allowed

No inline `<script>`, no `on*=` attribute, no CDN copy of Flowbite: the content security policy
blocks all three. Flowbite's JS is the vendored file listed in `VENDORED.md`.
