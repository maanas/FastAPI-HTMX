#!/usr/bin/env bash
# Managed by ~/bin/ecc.sh (overwritten on re-run).
# SessionStart (compact): puts the working directory, git state and the State and Pending
# sections of TODO.md (everything above "## Done") back into context so work resumes from
# TODO.md instead of from a lossy summary.
set -euo pipefail

dir="${CLAUDE_PROJECT_DIR:-$PWD}"
todo="$dir/TODO.md"
[[ -f "$todo" ]] || exit 0

context="Working directory: $dir
Branch: $(git -C "$dir" branch --show-current 2>/dev/null)
Uncommitted files: $(git -C "$dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

TODO.md, State and Pending only (Done is left out; read it with: sed -n '/^## Done/,\$p' TODO.md).
Resume from the Next line in State:

$(sed '/^## Done/,$d' "$todo")"

jq -n --arg c "$context" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $c}}'
