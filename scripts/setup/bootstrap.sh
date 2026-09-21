#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMMON_LIB="$ROOT_DIR/scripts/setup/lib/common.sh"
today="$(date +%F)"
session_file="$ROOT_DIR/memory/sessions/$today.md"

# shellcheck source=/dev/null
source "$COMMON_LIB"

print_section() {
  local title="$1"
  echo
  echo "== $title =="
}

echo "== AI Project Bootstrap =="
echo "root: $ROOT_DIR"
echo

"$ROOT_DIR/install.sh"
print_required_paths "$ROOT_DIR"

if [[ ! -f "$session_file" ]]; then
  cat > "$session_file" <<EOF2
# Session Log - $today

## Goal

- 

## Scope

- 

## Out of Scope

- 

## Stop Conditions

- 

## Loop State

- current:
- last_verified_at:
- step_budget:
- retry_budget:

## Unresolved / Open Questions

- 

## Notes

- 

## Decisions

- 

## Next

- 

## Resume From

- next_state:
- required_context:
- blocking_reason:
EOF2
  echo "[created] memory/sessions/$today.md"
else
  echo "[ok] memory/sessions/$today.md"
fi

print_section "Read First"
sed -n '1,40p' "$ROOT_DIR/AGENTS.md" || true

if [[ -f "$ROOT_DIR/CLAUDE.md" ]]; then
  print_section "Claude Adapter"
  sed -n '1,24p' "$ROOT_DIR/CLAUDE.md" || true
fi

print_section "Current State"
sed -n '1,80p' "$ROOT_DIR/memory/current-state.md" || true

if [[ -f "$ROOT_DIR/docs/project-structure.md" ]]; then
  print_section "Structure Guide"
  sed -n '1,120p' "$ROOT_DIR/docs/project-structure.md" || true
fi

print_section "App Workspace"
echo "app/ is the primary deployable workspace."
print_app_project_markers "$ROOT_DIR"
if [[ -f "$ROOT_DIR/app/README.md" ]]; then
  sed -n '1,80p' "$ROOT_DIR/app/README.md" || true
fi

print_section "Autonomy Reminder"
echo "Before starting, define Goal / Scope / Out of Scope / Stop Conditions in memory/sessions."
echo "Within that boundary, proceed without asking for every small step."
echo "Keep Loop State current, and leave Resume From when stopping or blocking."
echo "Do not leave unresolved questions only in chat context; record them in the session file."

print_section "Root Project Type"
print_root_project_markers "$ROOT_DIR"

print_section "Session File"
echo "$session_file"

print_section "Git Status"
if [[ -d "$ROOT_DIR/.git" ]]; then
  git -C "$ROOT_DIR" status --short || true
else
  echo "[info] no .git directory detected"
fi
