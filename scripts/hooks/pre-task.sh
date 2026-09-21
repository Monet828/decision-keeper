#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
today="$(date +%F)"
session_file="$ROOT_DIR/memory/sessions/$today.md"

mkdir -p "$ROOT_DIR/memory/sessions"

if [[ ! -f "$session_file" ]]; then
  cat > "$session_file" <<EOF
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
EOF
fi

echo "== Pre Task =="
echo "session: $session_file"
echo "Confirm Goal / Scope / Out of Scope / Stop Conditions before starting."
echo "Set Loop State and budgets if the task is expected to run for more than a few steps."
echo "If there are open questions, record them before they disappear into context."
echo "If already defined, proceed within that boundary."
