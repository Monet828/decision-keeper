#!/usr/bin/env bash
# Hand one read-only investigation to Codex and return a report whose
# load-bearing fields are derived mechanically rather than self-reported.
#
# `skills/delegating-to-codex/SKILL.md` decides *whether* to delegate and what
# to ask for. This script exists because that skill's report contract says
# status, files_modified, and command exit codes must be mechanical -- and
# prose alone does not make them so. Everything here is the mechanical half.
#
#   ./scripts/codex/delegate.sh "<task prompt>"
#   ./scripts/codex/delegate.sh --label audit-auth "<task prompt>"
#   ./scripts/codex/delegate.sh --resume <THREAD_ID> "<follow-up>"
#
# Exit codes: 0 delegation completed | 1 Codex failed | 2 cannot delegate
#             3 read-only invariant violated (files changed on disk)
set -uo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: delegate.sh [--label <name>] [--resume <THREAD_ID>] [--cd <DIR>] <task prompt>

  --label   name for the log file (default: task)
  --resume  continue an existing Codex thread instead of starting a new one
  --cd      repository root to hand to Codex (default: current directory)

The sandbox is always read-only and cannot be overridden. See
skills/delegating-to-codex/SKILL.md section 6 for why.
USAGE
}

LABEL="task"
RESUME_ID=""
WORK_DIR="$(pwd)"
PROMPT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --label)  LABEL="${2:-}"; shift 2 || { usage; exit 2; } ;;
    --resume) RESUME_ID="${2:-}"; shift 2 || { usage; exit 2; } ;;
    --cd)     WORK_DIR="${2:-}"; shift 2 || { usage; exit 2; } ;;
    -h|--help) usage; exit 0 ;;
    --) shift; PROMPT="${*:-}"; break ;;
    -*) echo "delegate.sh: unknown option: $1" >&2; usage; exit 2 ;;
    *)  PROMPT="$*"; break ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo "delegate.sh: no task prompt given" >&2
  usage
  exit 2
fi

# ---- refuse rather than degrade ----
if ! command -v codex >/dev/null 2>&1; then
  echo "delegate.sh: codex is not on PATH -- do the work yourself" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "delegate.sh: python3 is required to parse Codex output mechanically" >&2
  exit 2
fi
if [[ ! -d "$WORK_DIR" ]]; then
  echo "delegate.sh: not a directory: $WORK_DIR" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="$SCRIPT_DIR/report-schema.json"

LOG_DIR="${CODEX_DELEGATE_LOG_DIR:-${TMPDIR:-/tmp}}"
mkdir -p "$LOG_DIR"
STAMP="$(date '+%Y%m%d-%H%M%S')"
LOG="$LOG_DIR/codex-$LABEL-$STAMP.jsonl"
ERR="$LOG_DIR/codex-$LABEL-$STAMP.err"

# ---- record the tree before, so files_modified comes from git, not from Codex ----
in_git_repo() { git -C "$WORK_DIR" rev-parse --git-dir >/dev/null 2>&1; }
tree_state() {
  if in_git_repo; then
    git -C "$WORK_DIR" rev-parse HEAD 2>/dev/null
    git -C "$WORK_DIR" status --porcelain 2>/dev/null
  fi
}
BEFORE="$(tree_state)"

# ---- run ----
# stdin is redirected from /dev/null deliberately. `codex exec` reads the
# prompt from stdin when none is piped-in cleanly, and in a non-interactive
# parent it will block forever waiting for input that never arrives. This was
# observed as an indefinite hang, not an error.
set -- exec --json --sandbox read-only --cd "$WORK_DIR" --output-schema "$SCHEMA"
if [[ -n "$RESUME_ID" ]]; then
  codex "$@" resume "$RESUME_ID" "$PROMPT" </dev/null >"$LOG" 2>"$ERR"
else
  codex "$@" "$PROMPT" </dev/null >"$LOG" 2>"$ERR"
fi
CODEX_EXIT=$?

AFTER="$(tree_state)"

# ---- read-only invariant ----
if [[ "$BEFORE" != "$AFTER" ]]; then
  echo "delegate.sh: FILES CHANGED under --sandbox read-only." >&2
  echo "  This must not happen. Inspect the tree before trusting anything here." >&2
  echo "  log: $LOG" >&2
  git -C "$WORK_DIR" status --porcelain >&2 2>/dev/null || true
  exit 3
fi

# ---- report ----
CODEX_EXIT="$CODEX_EXIT" LOG="$LOG" ERR="$ERR" LABEL="$LABEL" \
python3 - <<'PY'
import json, os, sys

log = os.environ["LOG"]
codex_exit = int(os.environ["CODEX_EXIT"])

thread_id = None
commands = []
errors = []
usage = {}
final_text = None

with open(log, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        if etype == "thread.started":
            thread_id = event.get("thread_id")
        elif etype == "turn.completed":
            usage = event.get("usage") or {}
        elif etype == "item.completed":
            item = event.get("item") or {}
            itype = item.get("type")
            if itype == "command_execution":
                commands.append({
                    "command": item.get("command"),
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status"),
                })
            elif itype == "agent_message":
                final_text = item.get("text")
            elif itype == "error":
                errors.append(item.get("message"))

# status comes from the process exit code. `error` items are NOT used: Codex
# emits them for advisory notices (e.g. "Skill descriptions were shortened"),
# so treating their presence as failure reports healthy runs as broken.
status = "success" if codex_exit == 0 else "failure"

report = None
if final_text:
    try:
        report = json.loads(final_text)
    except json.JSONDecodeError:
        report = {"summary": final_text}

failed = [c for c in commands if c.get("exit_code") not in (0, None)]

out = {
    "status": status,
    "exit_code": codex_exit,
    "thread_id": thread_id,
    "files_modified": [],          # verified against git above, not self-reported
    "commands": commands,
    "commands_failed": len(failed),
    "notices": errors,
    "usage": usage,
    "log": log,
    "report": report,
}
json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
print()

print("", file=sys.stderr)
print(f"status:   {status} (exit {codex_exit})", file=sys.stderr)
print(f"commands: {len(commands)} run, {len(failed)} non-zero", file=sys.stderr)
if thread_id:
    print(f"resume:   ./scripts/codex/delegate.sh --resume {thread_id} \"<follow-up>\"", file=sys.stderr)
print(f"log:      {log}", file=sys.stderr)
if errors:
    print(f"notices:  {len(errors)} (advisory; they do not mean failure)", file=sys.stderr)
PY

exit "$CODEX_EXIT"
