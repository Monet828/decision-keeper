#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
today="$(date +%F)"
session_file="$ROOT_DIR/memory/sessions/$today.md"

echo "== Resume Loop =="
echo "Read in this order:"
echo "1. memory/current-state.md"
echo "2. latest session file"
echo "3. Resume From"
echo
echo "Current state file:"
echo "$ROOT_DIR/memory/current-state.md"
echo
echo "Session file:"
echo "$session_file"
echo

if [[ -f "$session_file" ]]; then
  awk '
    /^## Loop State$/ { printing=1 }
    /^## Unresolved \/ Open Questions$/ { exit }
    printing { print }
  ' "$session_file" || true
  awk '
    /^## Unresolved \/ Open Questions$/ { printing=1 }
    /^## Notes$/ { exit }
    printing { print }
  ' "$session_file" || true
  echo
  sed -n '/## Resume From/,$p' "$session_file" || true
else
  echo "[missing] $session_file"
fi
