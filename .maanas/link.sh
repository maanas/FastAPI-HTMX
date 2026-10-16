#!/usr/bin/env bash
set -euo pipefail
# Symlink this repo's own skills and agents into .claude/ so Claude Code discovers them:
# root skills/ (flowbite, htmx-patterns, new-page), .maanas/skills/ and .maanas/agents/.
# Prunes links whose source is gone. Never overwrites a real (ecc-copied) file. Safe to re-run.
cd "$(dirname "$0")/.."

# link_all <src glob> <dest dir>; sources are repo-root relative, links point ../../<src>
link_all() {
  local pattern=$1 dest=$2
  mkdir -p "$dest"
  for link in "$dest"/*; do
    if [ -L "$link" ] && [ ! -e "$link" ]; then rm "$link"; echo "pruned: $link"; fi
  done
  for src in $pattern; do
    [ -e "$src" ] || continue
    local name target
    name=$(basename "$src")
    [ "$name" = _template ] && continue
    target="$dest/$name"
    if [ -L "$target" ]; then continue
    elif [ -e "$target" ]; then echo "skip (real file exists): $target" >&2
    else ln -s "../../${src%/}" "$target"; echo "linked: $target"
    fi
  done
}

link_all "skills/*/" .claude/skills
link_all ".maanas/skills/*/" .claude/skills
link_all ".maanas/agents/*.md" .claude/agents
