# Browser pass (director only; workers have no browser)

- Needs the Claude in Chrome extension connected (`/chrome`, restart the session if tools are missing).
- Use a scratch database: `DATABASE_URL` pointing at a file under the scratchpad plus throwaway
  settings there; never move or delete `users.db`, never touch `.env`.
- Native `confirm()` is invisible to the extension. Replace `window.confirm` with a stub that records
  the text and returns true or false; `hx-confirm` calls it, so both answers can be tested.
- Resize to phone width, then wait; prefer `javascript_tool` (`element.click()`, reading Alpine data,
  `input.validity`) over clicks by coordinate.
- Check the console on every page: no CSP violation, no "CSP Parser Error", no "Undefined variable".
- Test repeated identical errors, stale messages after a fix, and each status (400, 403, 422, network).
- Anything needing a service (MinIO, Docker) that is down goes to TODO.md as untested.
