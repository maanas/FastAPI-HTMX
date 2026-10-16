#!/usr/bin/env bash
# Managed by ~/bin/ecc.sh (overwritten on re-run).
# Context budget guard. Reads the session transcript, takes the context size of the last main-thread
# model call (input + cache read + cache write tokens) and, past CONTEXT_LIMIT (default 85000):
#   UserPromptSubmit / PostToolUse: tells Claude to write its state to TODO.md now
#     (PostToolUse only once per 10k step).
#   Stop: shows the user that auto-compaction is near.
# Auto-compaction runs at 100k (autoCompactWindow in settings.json); after it the SessionStart
# compact hook (resume-context.sh) puts TODO.md back, so TODO.md must be current before then.
set -euo pipefail

limit="${CONTEXT_LIMIT:-85000}"
step=10000
input="$(cat)"
event="$(jq -r '.hook_event_name // empty' <<<"$input")"
transcript="$(jq -r '.transcript_path // empty' <<<"$input")"
session="$(jq -r '.session_id // "unknown"' <<<"$input")"
[[ -n "$transcript" && -f "$transcript" ]] || exit 0

# Only usage after the last compact_boundary counts; before it the context was larger.
tokens="$(grep -E '"usage"|"compact_boundary"' "$transcript" | jq -s -r '
  (map(.subtype == "compact_boundary") | rindex(true)) as $b
  | (if $b == null then . else .[$b + 1:] end)
  | [.[] | select(.type == "assistant" and (.isSidechain | not) and .message.usage)] | last
  | .message.usage
  | if . == null then 0
    else (.input_tokens // 0) + (.cache_read_input_tokens // 0) + (.cache_creation_input_tokens // 0)
    end')"
(( tokens >= limit )) || exit 0

k=$(( tokens / 1000 ))
note="Context is ${k}k tokens; auto-compaction runs at 100k and keeps only TODO.md. \
Write the current state to TODO.md now: what is done, what is in progress (files, next step), \
decisions made. Then continue the current task."

case "$event" in
  UserPromptSubmit)
    jq -n --arg c "$note" --arg m "Context ${k}k: TODO.md checkpoint before auto-compact." \
      '{systemMessage: $m, hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $c}}'
    ;;
  PostToolUse)
    marker="${TMPDIR:-/tmp}/claude-context-guard-${session}"
    bucket=$(( tokens / step ))
    last="$(cat "$marker" 2>/dev/null || echo 0)"
    (( bucket > last )) || exit 0
    echo "$bucket" >"$marker"
    jq -n --arg c "$note" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $c}}'
    ;;
  Stop)
    jq -n --arg m "Context ${k}k tokens: auto-compaction at 100k, TODO.md is the state." \
      '{systemMessage: $m}'
    ;;
esac
