# Attributes

## Target and swap

- Always name the target: `hx-target="#roles-table"`.
- `hx-swap="outerHTML"` when the partial's root is the target itself; `innerHTML` when it is the
  target's content; `beforeend` to append a row; `delete` to remove the target.
- A second region in the same response is out-of-band: `hx-swap-oob="true"` on an element whose
  `id` already exists on the page (a counter, the toast region).
- `hx-select` picks a fragment out of a larger response; prefer returning the right partial.

## Triggers

Use modifiers instead of JS:

| Need | `hx-trigger` |
|---|---|
| Search as you type | `keyup changed delay:300ms` (with `hx-sync="this:replace"`) |
| Load when scrolled into view | `revealed` |
| Poll | `every 30s` |
| React to a server event | `<event> from:body` (the event named in `HX-Trigger`) |
| Load once on render | `load` |

## Forms

- `hx-post` / `hx-put` on the `<form>`, not on the button, so Enter submits and fields are included.
- `hx-disabled-elt="find button[type=submit]"` and `hx-indicator` so a form is not sent twice.
- `hx-confirm` on destructive actions.
- In htmx 2 a `DELETE` sends its values as query parameters, not a form body: read them from the
  query string, or put the id in the URL.
- `hx-headers` on `<body>` is inherited by every request; that is where `X-CSRF-Token` is set.

## Navigation

- `hx-boost="true"` on the shell's nav turns links into swaps of `<body>`; a boosted request needs
  the full page.
- `hx-push-url="true"` on a swap that changes what the page shows, so reload and back work.

## htmx 2 differences from 1.9

- Extensions are separate files, not part of the core; vendor each one that is used.
- `hx-on` is written `hx-on:<event>` (and is not allowed here anyway, see `security.md`).
- Cross-origin requests are blocked by default (`selfRequestsOnly`).
- 4xx and 5xx are not swapped unless `responseHandling` allows the code.
