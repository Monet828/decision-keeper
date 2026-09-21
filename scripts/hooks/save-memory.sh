#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "$ROOT_DIR/memory/sessions"

today="$(date +%F)"
session_file="$ROOT_DIR/memory/sessions/$today.md"

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

timestamp="$(date '+%Y-%m-%d %H:%M')"

if [[ -t 0 ]]; then
  echo "== Save Memory =="
  echo "session: $session_file"
  echo

  read -r -p "Summary (one line, optional): " summary
  read -r -p "Boundary hit? (optional): " boundary
  read -r -p "Decision to promote (optional): " decision
  read -r -p "Next action (optional): " next_action
  read -r -p "Next state (optional): " next_state
  read -r -p "Required context for resume (optional): " required_context
  read -r -p "Blocking reason (optional): " blocking_reason
  read -r -p "Unresolved question (optional): " unresolved

  {
    echo
    echo "## Checkpoint - $timestamp"
    echo
    if [[ -n "${summary:-}" ]]; then
      echo "- Summary: $summary"
    fi
    if [[ -n "${boundary:-}" ]]; then
      echo "- Boundary Hit: $boundary"
    fi
    if [[ -n "${decision:-}" ]]; then
      echo "- Decision Candidate: $decision"
    fi
    if [[ -n "${next_action:-}" ]]; then
      echo "- Next Action: $next_action"
    fi
    if [[ -n "${next_state:-}" ]]; then
      echo "- Next State: $next_state"
    fi
    if [[ -n "${required_context:-}" ]]; then
      echo "- Required Context: $required_context"
    fi
    if [[ -n "${blocking_reason:-}" ]]; then
      echo "- Blocking Reason: $blocking_reason"
    fi
    if [[ -n "${unresolved:-}" ]]; then
      echo "- Unresolved Question: $unresolved"
    fi
    if [[ -z "${summary:-}${boundary:-}${decision:-}${next_action:-}${next_state:-}${required_context:-}${blocking_reason:-}${unresolved:-}" ]]; then
      echo "- No structured input provided."
    fi
  } >> "$session_file"

  echo
  echo "Updated: $session_file"
  echo "Promote durable decisions to memory/decisions.md or docs/adr/ as needed."
else
  echo "Append notes to: $session_file"
  echo "Record boundary hits, next state, and promote durable decisions to memory/decisions.md or docs/adr/ as needed."
fi
