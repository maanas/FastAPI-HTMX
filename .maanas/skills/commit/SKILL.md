---
name: commit
description: Creates a local git commit in this repo's message style from the current step's changes, refusing secrets and other forbidden files. Never pushes.
---
# Commit

1. `git status` and `git diff` (staged and unstaged) to see what changed.
2. Refuse to commit and report back if the change contains any of:
   - secrets, credentials, keys, tokens, or any `.env` file
   - a database file (`*.db`), uploads, logs or a virtualenv
   - anything under `theme/flowbite/` other than the submodule pointer
   - large binaries that are not a vendored asset listed in `VENDORED.md`
3. Stage only the files that belong to this step (`git add <paths>`; never `git add -A` unless every change belongs). A vendored file goes in together with its `VENDORED.md` row, a model change together with its migration.
4. Write the message in the repo's style (see `git log --format=%s -5 main`):
   - summary: `type: what changed`, e.g. `feat: vendor htmx 2 and Alpine under app/static`, at most 72 characters; types are `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `build`
   - plain hyphens and straight quotes only; no em dashes, no emoji codes
   - body only when the why is not obvious
   - no AI attribution: no `Co-Authored-By` trailer for an AI, no "Generated with" line, no session link
5. `git commit` with the configured git user. Never `--amend`, `--no-verify`, `--author`, or push.
6. Report the commit hash and message.
