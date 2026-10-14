# Flowbite and Alpine with HTMX

## Flowbite after a swap

Flowbite binds its `data-*` components (modal, drawer, dropdown, tabs, tooltip) once, at page load.
Markup that arrives in a swap is not bound.

- One listener in `app/static/js/` on `htmx:afterSettle` runs Flowbite's init for the swapped
  content. Check how the vendored build exposes it (`initFlowbite`, or the per-component
  `initModals`, `initDropdowns`) in `theme/flowbite/content/getting-started/javascript.md`,
  lines 190 to 215.
- Never a listener per page, never a script in the partial.
- A modal or drawer that the swap replaces while it is open leaves its backdrop behind: close it
  first (an `HX-Trigger` event the shared JS handles), or swap only its body.

## Alpine

- Alpine initialises swapped-in elements by itself; nothing to call.
- Components are registered with `Alpine.data("name", () => ({...}))` in `app/static/js/` and used
  as `x-data="name"`. `login` and `register` in `components.js` are the pattern.
- With the Alpine CSP build an attribute holds a property name or a method call only: no object
  literal in `x-data`, no expression with operators, no assignment in `@click`. Put the logic in a
  method.
- Server data reaches a component through `data-*` attributes on the element (`this.$el.dataset`),
  not through Jinja inside a script or inside `x-data`.
- Alpine owns local UI state (open, loading, a field's error flag). Anything the server knows is
  fetched with HTMX, not kept in Alpine.

## htmx events

| Event | Use |
|---|---|
| `htmx:configRequest` | Add a header or value to every request |
| `htmx:afterSettle` | Initialise swapped content; `components.js` reads `HX-Trigger` here to show alerts |
| `htmx:responseError` | Error alerts come from the `showAlert` event, with no swap |
| `htmx:sendError` | Network failure |
| A name from `HX-Trigger` | Fired on the triggering element and bubbles to `body` |

Listen on `document.body` in a file under `app/static/js/`. One listener per event for the whole
app.

## Focus

After a swap that replaces the focused element, focus is lost. Give the replaced element a stable
`id` (htmx restores focus by `id`), or set `autofocus` on the field the user should land on.
