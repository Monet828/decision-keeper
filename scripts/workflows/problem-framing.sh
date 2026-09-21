#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
mkdir -p "$ROOT_DIR/memory"
problem_map="$ROOT_DIR/memory/problem-map.md"

if [[ ! -f "$problem_map" ]]; then
  cat > "$problem_map" <<EOF
# Problem Map

## Current Truth

- 

## Goal

- 

## Biggest Problem

- 

## North Star

- 

## Necessary Conditions

- [ ] 
- [ ] 
- [ ] 

## Subproblems

- [ ] 
- [ ] 
- [ ] 

## Current Subproblem

- 

## Traceability

- This subproblem satisfies:

## Why This One Now

- 

## Evidence / Findings

- 

## Unresolved / Open Questions

- 

## Next Subproblem Candidates

- 

## Re-synthesis Check

- If these branches are solved, does North Star really become solvable?
EOF
fi

timestamp="$(date '+%Y-%m-%d %H:%M')"

echo "== Problem Framing =="
echo "file: $problem_map"
echo

if [[ -t 0 ]]; then
  read -r -p "Concept (optional): " concept
  read -r -p "Goal (optional): " goal
  read -r -p "Biggest problem (optional): " biggest_problem
  read -r -p "North Star (optional): " north_star
  read -r -p "Necessary condition satisfied by current subproblem (optional): " traceability
  read -r -p "Current subproblem (optional): " current_subproblem
  read -r -p "Why this one now? (optional): " why_now
  read -r -p "Evidence / finding (optional): " evidence
  read -r -p "Open question (optional): " open_question
  read -r -p "Next subproblem candidate (optional): " next_candidate
  read -r -p "Re-synthesis check (optional): " resynthesis_check

  {
    echo
    echo "## Checkpoint - $timestamp"
    echo
    if [[ -n "${concept:-}" ]]; then
      echo "- Concept: $concept"
    fi
    if [[ -n "${goal:-}" ]]; then
      echo "- Goal: $goal"
    fi
    if [[ -n "${biggest_problem:-}" ]]; then
      echo "- Biggest Problem: $biggest_problem"
    fi
    if [[ -n "${north_star:-}" ]]; then
      echo "- North Star: $north_star"
    fi
    if [[ -n "${current_subproblem:-}" ]]; then
      echo "- Current Subproblem: $current_subproblem"
    fi
    if [[ -n "${traceability:-}" ]]; then
      echo "- Traceability: $traceability"
    fi
    if [[ -n "${why_now:-}" ]]; then
      echo "- Why This One Now: $why_now"
    fi
    if [[ -n "${evidence:-}" ]]; then
      echo "- Evidence / Finding: $evidence"
    fi
    if [[ -n "${open_question:-}" ]]; then
      echo "- Open Question: $open_question"
    fi
    if [[ -n "${next_candidate:-}" ]]; then
      echo "- Next Subproblem Candidate: $next_candidate"
    fi
    if [[ -n "${resynthesis_check:-}" ]]; then
      echo "- Re-synthesis Check: $resynthesis_check"
    fi
    if [[ -z "${concept:-}${goal:-}${biggest_problem:-}${north_star:-}${traceability:-}${current_subproblem:-}${why_now:-}${evidence:-}${open_question:-}${next_candidate:-}${resynthesis_check:-}" ]]; then
      echo "- No structured input provided."
    fi
  } >> "$problem_map"

  echo
  echo "Updated: $problem_map"
else
  echo "Append checkpoints to: $problem_map"
fi
