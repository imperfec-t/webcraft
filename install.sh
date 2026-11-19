#!/usr/bin/env bash
# Copy the webcraft skills into an agent's skills folder, no Python needed.
#   ./install.sh claude|codex|gemini|copilot|agents [--project]   (default: claude, user scope)
#   ./install.sh --dest DIR
# With Python, prefer: webcraft install <agent>  (also does Cursor, Windsurf and AGENTS.md).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="claude"; SCOPE="user"; DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) SCOPE="project" ;;
    --dest) [ $# -ge 2 ] || { echo "error: --dest needs a directory" >&2; exit 2; }; DEST="$2"; shift ;;
    -h|--help) sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "error: unknown option $1" >&2; exit 2 ;;
    *) AGENT="$1" ;;
  esac
  shift
done
if [ -z "$DEST" ]; then
  case "$AGENT:$SCOPE" in
    claude:user) DEST="$HOME/.claude/skills" ;;   claude:project) DEST=".claude/skills" ;;
    codex:user|agents:user) DEST="$HOME/.agents/skills" ;; codex:project|agents:project) DEST=".agents/skills" ;;
    gemini:user) DEST="$HOME/.gemini/skills" ;;   gemini:project) DEST=".gemini/skills" ;;
    copilot:user) DEST="$HOME/.copilot/skills" ;; copilot:project) DEST=".github/skills" ;;
    *) echo "error: agent must be claude, codex, gemini, copilot or agents" >&2; exit 2 ;;
  esac
fi
mkdir -p "$DEST"
n=0
for d in "$ROOT"/skills/*/; do
  [ -f "$d/SKILL.md" ] || continue
  name="$(basename "$d")"
  if [ -d "$DEST/$name" ] && [ ! -f "$DEST/$name/.webcraft" ]; then
    echo "skip   $DEST/$name (exists and was not installed by webcraft)"; continue
  fi
  rm -rf "${DEST:?}/$name"
  cp -R "$d" "$DEST/$name"
  echo "installed by webcraft (install.sh)" > "$DEST/$name/.webcraft"
  echo "install $DEST/$name"; n=$((n + 1))
done
echo "Done: $n skill(s) in $DEST. Restart the agent to pick them up."
