#!/usr/bin/env bash
# PreToolUse guard for Bash: keeps main merge-request only.
# Blocks commits and merges while on main, pushes to main, force pushes and --no-verify.
# Matches only real `git <subcommand>` calls, not words inside messages or paths.
# Fails closed: input it cannot parse blocks the command.
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty') || {
  echo "git-guard: cannot parse the hook input, command blocked. Check that jq is installed." >&2
  exit 2
}
case "$cmd" in *git*) ;; *) exit 0 ;; esac

block() { echo "git-guard: $1" >&2; exit 2; }
# `git`, optional global options (-C dir, -c key=val), then the subcommand.
G='(^|[;&|(]|&&|\|\|)[[:space:]]*git([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+)*[[:space:]]+'
has() { printf '%s' "$cmd" | grep -Eq "$1"; }

branch=$(git -C "${CLAUDE_PROJECT_DIR:-.}" symbolic-ref --short HEAD 2>/dev/null || true)
on_main=false
[ "$branch" = "main" ] || [ "$branch" = "master" ] && on_main=true

has "${G}(commit|push|merge)[^;&|]*--no-verify" &&
  block "--no-verify is not allowed; fix what the git hook reports."
has "${G}push[^;&|]*(--force|[[:space:]]-f([[:space:]]|$)|[[:space:]]\+[^[:space:]])" &&
  block "force push is not allowed."
has "${G}push[^;&|]*[[:space:]:](main|master)([[:space:]]|$)" &&
  block "pushing to main is not allowed. Push a branch and open a merge request."
has "${G}(switch|checkout)[[:space:]]+(main|master)([[:space:]]|$)" && on_main=true
has "${G}(switch[[:space:]]+(-c|--create)|checkout[[:space:]]+-b)[[:space:]]" && on_main=false
if $on_main; then
  has "${G}(commit|merge|rebase|cherry-pick|revert|am)([[:space:]]|$)" &&
    block "no commits or merges on main. Create a branch: git switch -c <name>"
  has "${G}push([[:space:]]|$)" && ! has "${G}push[^;&|]*[[:space:]]origin[[:space:]]+[^[:space:]-]" &&
    block "on main: push a feature branch instead."
fi
exit 0
