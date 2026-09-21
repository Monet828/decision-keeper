#!/usr/bin/env bash
# Run Codex's built-in code review and keep the output out of context.
#
# This is a second model's opinion, not a verdict. Run it *after* forming your
# own -- see skills/delegating-to-codex/SKILL.md section 4 for how to combine
# the two, and why order matters.
#
#   ./scripts/codex/review.sh --uncommitted
#   ./scripts/codex/review.sh --base main
#   ./scripts/codex/review.sh --commit <SHA>
#
# Exit codes: 0 review ran | 1 Codex failed | 2 cannot review
#             3 read-only invariant violated (files changed on disk)
set -uo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: review.sh (--uncommitted | --base <REF> | --commit <SHA>) [--cd <DIR>]

Exactly one target must be given. The review is always read-only.
USAGE
}

TARGET=()
WORK_DIR="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --uncommitted) TARGET=(--uncommitted); shift ;;
    --base)        TARGET=(--base "${2:-}"); shift 2 || { usage; exit 2; } ;;
    --commit)      TARGET=(--commit "${2:-}"); shift 2 || { usage; exit 2; } ;;
    --cd)          WORK_DIR="${2:-}"; shift 2 || { usage; exit 2; } ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "review.sh: unexpected argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ ${#TARGET[@]} -eq 0 ]]; then
  echo "review.sh: no review target given" >&2
  usage
  exit 2
fi
if ! command -v codex >/dev/null 2>&1; then
  echo "review.sh: codex is not on PATH -- review it yourself" >&2
  exit 2
fi
if [[ ! -d "$WORK_DIR" ]]; then
  echo "review.sh: not a directory: $WORK_DIR" >&2
  exit 2
fi

LOG_DIR="${CODEX_DELEGATE_LOG_DIR:-${TMPDIR:-/tmp}}"
mkdir -p "$LOG_DIR"
STAMP="$(date '+%Y%m%d-%H%M%S')"
LOG="$LOG_DIR/codex-review-$STAMP.md"

tree_state() {
  if git -C "$WORK_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$WORK_DIR" rev-parse HEAD 2>/dev/null
    git -C "$WORK_DIR" status --porcelain 2>/dev/null
  fi
}
BEFORE="$(tree_state)"

# stdin from /dev/null: see the note in delegate.sh -- codex exec otherwise
# blocks forever waiting on stdin in a non-interactive parent.
codex exec --sandbox read-only --cd "$WORK_DIR" review "${TARGET[@]}" \
  </dev/null >"$LOG" 2>&1
CODEX_EXIT=$?

if [[ "$BEFORE" != "$(tree_state)" ]]; then
  echo "review.sh: FILES CHANGED during a read-only review. Inspect the tree." >&2
  echo "  log: $LOG" >&2
  exit 3
fi

echo "status: $([[ $CODEX_EXIT -eq 0 ]] && echo success || echo failure) (exit $CODEX_EXIT)" >&2
echo "log:    $LOG" >&2
echo "" >&2
echo "Read the log, then decide per skills/delegating-to-codex/SKILL.md section 4:" >&2
echo "  overlapping findings -> higher confidence; act on these first" >&2
echo "  diverging findings   -> judge individually; Codex is not automatically right" >&2
echo "  Codex-only findings  -> either your blind spot or its misreading; check the evidence" >&2

exit "$CODEX_EXIT"
