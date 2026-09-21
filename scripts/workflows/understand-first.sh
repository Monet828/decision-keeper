#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
mkdir -p "$ROOT_DIR/memory"
understanding_map="$ROOT_DIR/memory/understanding-map.md"

if [[ ! -f "$understanding_map" ]]; then
  cat > "$understanding_map" <<'EOF'
# Understanding Map

## Target

- 

## Why This Area Matters

- 

## Files Read

- 

## Related Docs

- 

## Related Decisions

- 

## Current Behavior

- 

## Responsibilities

- 

## Inputs / Outputs

- Inputs:
- Outputs:

## Dependencies

- 

## Risks

- 

## Unknowns

- 

## Assumptions

- 

## Safe Change Boundary

- 

## Next Reading Target

- 

## Resume From

- next_state:
- required_context:
- blocking_reason:
EOF
fi

target_area="${1:-}"
timestamp="$(date '+%Y-%m-%d %H:%M')"

echo "== Understand First =="
echo "file: $understanding_map"
echo
echo "Suggested reading order:"
echo "- AGENTS.md"
echo "- memory/current-state.md"
echo "- docs/"
echo "- memory/decisions.md"
echo "- src/"
echo "- tests/"
echo

if [[ -n "$target_area" ]]; then
  echo "target: $target_area"
fi

echo
echo "Before implementation, confirm:"
echo "- Files read is not empty"
echo "- Current behavior is described"
echo "- Unknowns are recorded"
echo "- Safe change boundary is written for non-trivial changes"

if [[ -t 0 ]]; then
  read -r -p "Target area (optional): " prompt_target
  read -r -p "Files read summary (optional): " files_read
  read -r -p "Current behavior summary (optional): " current_behavior
  read -r -p "Main unknown (optional): " unknown
  read -r -p "Safe change boundary (optional): " boundary
  read -r -p "Next reading target (optional): " next_reading

  {
    echo
    echo "## Checkpoint - $timestamp"
    echo
    if [[ -n "${target_area:-}" ]]; then
      echo "- Initial Target Argument: $target_area"
    fi
    if [[ -n "${prompt_target:-}" ]]; then
      echo "- Target Area: $prompt_target"
    fi
    if [[ -n "${files_read:-}" ]]; then
      echo "- Files Read Summary: $files_read"
    fi
    if [[ -n "${current_behavior:-}" ]]; then
      echo "- Current Behavior Summary: $current_behavior"
    fi
    if [[ -n "${unknown:-}" ]]; then
      echo "- Main Unknown: $unknown"
    fi
    if [[ -n "${boundary:-}" ]]; then
      echo "- Safe Change Boundary: $boundary"
    fi
    if [[ -n "${next_reading:-}" ]]; then
      echo "- Next Reading Target: $next_reading"
    fi
    if [[ -z "${target_area:-}${prompt_target:-}${files_read:-}${current_behavior:-}${unknown:-}${boundary:-}${next_reading:-}" ]]; then
      echo "- No structured input provided."
    fi
  } >> "$understanding_map"

  echo
  echo "Updated: $understanding_map"
else
  echo "Append checkpoints to: $understanding_map"
fi
