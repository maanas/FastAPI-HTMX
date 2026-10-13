---
name: pull-request
description: Pushes the current feature branch and opens a GitHub pull request into the fork's main with a full description (via gh, logged in as maanas). Use on your own when a task's last commit is done and retro has run. Never merges - maanas merges.
---
# Pull request

The pull request goes to the fork, `maanas/FastAPI-HTMX`, never to upstream
(`Hybridhash/FastAPI-HTMX`). `gh` picks the parent of a fork as the base by default, so `--repo` is
always given.

1. Check: `git rev-parse --abbrev-ref HEAD` is not `main` or `master`, `git status` is clean, and
   `git log --oneline origin/main..HEAD` lists the task's commits. Stop and report if any check fails.
2. Title: one plain sentence in the repo's commit style, at most 72 characters, no em dashes.
3. `gh api user --jq .login` must print `maanas`. If it prints another account, try
   `gh auth switch --user maanas`; if that fails, stop and ask the user to run
   `! gh auth login` as `maanas`. Never open the pull request from another account and never fall
   back to text for the user to paste.
4. Description, written to a temp file (`mktemp`), every section filled in:
   - `## What`: what changed, in a few lines.
   - `## Why`: the TODO item or the problem it closes.
   - `## Checked`: what was actually run and its result (ruff, pytest counts, pages requested).
   - `## Not done`: what is left open or was skipped, or "nothing".
   No AI attribution or session links.
5. Push the branch, then open the pull request:
   `git push -u origin <branch>`
   `gh pr create --repo maanas/FastAPI-HTMX --base main --head <branch> --title "<title>" --body-file <file>`
   If a pull request for the branch already exists, update it instead:
   `gh pr edit <branch> --repo maanas/FastAPI-HTMX --title "<title>" --body-file <file>`
6. Check with `gh pr view <branch> --repo maanas/FastAPI-HTMX` that the description is set, and
   report the URL. Merging is done by maanas only: never merge, approve or enable auto-merge on the
   pull request, and never push to `main`. If the push or
   `gh` is rejected, report the error; never retry with `--force` or `--no-verify`.
