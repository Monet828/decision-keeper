#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "$ROOT_DIR/memory/sessions"
today="$(date +%F)"
session_file="$ROOT_DIR/memory/sessions/$today.md"
timestamp="$(date '+%Y-%m-%d %H:%M')"

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

echo "== Verify Loop =="
echo "Use verifier.md as the review contract."
echo
echo "Check:"
echo "- requested outcome is actually complete"
echo "- changes stayed within agreed scope"
echo "- tests/lint/build were run or explicitly skipped"
echo "- hidden spec changes were not introduced"
echo "- memory/docs updates were applied if needed"
echo "- residual risks and unknowns are stated"
echo "- the sub-goal actually worked"
echo "- the sub-goal contributed to a necessary condition for North Star"
echo "- solving the remaining branches would still resolve North Star"
echo
echo "Reference:"
echo "$ROOT_DIR/agents/verifier.md"

if [[ -t 0 ]]; then
  echo
  read -r -p "Verification summary (optional): " summary
  read -r -p "Scope respected? (optional): " scope_status
  read -r -p "Tests/lint/build status (optional): " test_status
  read -r -p "Residual risk (optional): " residual_risk
  read -r -p "North Star contribution (optional): " north_star_contribution
  read -r -p "Re-synthesis check (optional): " resynthesis_check
  read -r -p "Unresolved question (optional): " unresolved

  {
    echo
    echo "## Verification - $timestamp"
    echo
    if [[ -n "${summary:-}" ]]; then
      echo "- Verification Summary: $summary"
    fi
    if [[ -n "${scope_status:-}" ]]; then
      echo "- Scope Status: $scope_status"
    fi
    if [[ -n "${test_status:-}" ]]; then
      echo "- Test Status: $test_status"
    fi
    if [[ -n "${residual_risk:-}" ]]; then
      echo "- Residual Risk: $residual_risk"
    fi
    if [[ -n "${north_star_contribution:-}" ]]; then
      echo "- North Star Contribution: $north_star_contribution"
    fi
    if [[ -n "${resynthesis_check:-}" ]]; then
      echo "- Re-synthesis Check: $resynthesis_check"
    fi
    if [[ -n "${unresolved:-}" ]]; then
      echo "- Unresolved Question: $unresolved"
    fi
    if [[ -z "${summary:-}${scope_status:-}${test_status:-}${residual_risk:-}${north_star_contribution:-}${resynthesis_check:-}${unresolved:-}" ]]; then
      echo "- No structured verification input provided."
    fi
  } >> "$session_file"

  echo
  echo "Verification notes appended to: $session_file"
fi
