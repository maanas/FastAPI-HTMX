#!/usr/bin/env bash
# PreToolUse guard: blocks edits to .env files.
# Fails closed: input it cannot parse blocks the edit. No here-strings (they need temp space).
input=$(cat)
filter='.tool_input.file_path // .tool_input.notebook_path // empty'
path=$(printf '%s' "$input" | jq -r "$filter") || {
  echo "protected-files: cannot parse the hook input, edit blocked. Check that jq is installed." >&2
  exit 2
}
[ -z "$path" ] && exit 0

case "$(basename "$path")" in
  .env.example) ;;
  .env | .env.*)
    echo "protected-files: $path holds secrets and is never edited." >&2
    exit 2
    ;;
esac
exit 0
