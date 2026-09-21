#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
mkdir -p "$ROOT_DIR/memory"
evidence_log="$ROOT_DIR/memory/evidence-log.md"

if [[ ! -f "$evidence_log" ]]; then
  cat > "$evidence_log" <<'EOF'
# Evidence Log

## Research Question

- 

## Scope

- 

## Sources Consulted

- Source:
  - Type:
  - Date:
  - URL or reference:
  - Why it matters:

## Facts

- Fact:
  - Source:
  - Date:

## Quotes or Summaries

- 

## Unknowns / Open Questions

- 

## Decision Impact

- 

## Resume From

- next_state:
- required_context:
- blocking_reason:
EOF
fi

research_question="${1:-}"
timestamp="$(date '+%Y-%m-%d %H:%M')"

echo "== Evidence First =="
echo "file: $evidence_log"
echo
if [[ -n "$research_question" ]]; then
  echo "research question: $research_question"
  echo
fi

echo "Before interpretation, confirm:"
echo "- Each important claim has a source"
echo "- Time-sensitive points have dates"
echo "- Facts and interpretation are separated"
echo "- Unknowns are explicitly listed"

if [[ -t 0 ]]; then
  read -r -p "Research question (optional): " prompt_question
  read -r -p "Source summary (optional): " source_summary
  read -r -p "Fact summary (optional): " fact_summary
  read -r -p "Quote or summary (optional): " quote_or_summary
  read -r -p "Open question (optional): " open_question
  read -r -p "Decision impact (optional): " decision_impact

  {
    echo
    echo "## Checkpoint - $timestamp"
    echo
    if [[ -n "${research_question:-}" ]]; then
      echo "- Initial Research Question: $research_question"
    fi
    if [[ -n "${prompt_question:-}" ]]; then
      echo "- Research Question: $prompt_question"
    fi
    if [[ -n "${source_summary:-}" ]]; then
      echo "- Source Summary: $source_summary"
    fi
    if [[ -n "${fact_summary:-}" ]]; then
      echo "- Fact Summary: $fact_summary"
    fi
    if [[ -n "${quote_or_summary:-}" ]]; then
      echo "- Quote or Summary: $quote_or_summary"
    fi
    if [[ -n "${open_question:-}" ]]; then
      echo "- Open Question: $open_question"
    fi
    if [[ -n "${decision_impact:-}" ]]; then
      echo "- Decision Impact: $decision_impact"
    fi
    if [[ -z "${research_question:-}${prompt_question:-}${source_summary:-}${fact_summary:-}${quote_or_summary:-}${open_question:-}${decision_impact:-}" ]]; then
      echo "- No structured input provided."
    fi
  } >> "$evidence_log"

  echo
  echo "Updated: $evidence_log"
else
  echo "Append checkpoints to: $evidence_log"
fi
