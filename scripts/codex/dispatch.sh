#!/usr/bin/env bash
# Pop one item from the codex verification queue (see discover.sh) and hand
# it to delegate.sh as a fact-check task. This is the human-triggered half
# of the two-layer design: discover.sh finds candidates on its own schedule,
# but nothing reaches Codex until a human runs this.
#
#   ./scripts/codex/dispatch.sh --list      # show pending items
#   ./scripts/codex/dispatch.sh --next      # dispatch the oldest pending item
#   ./scripts/codex/dispatch.sh --id <ID>   # dispatch one specific item
#
# Exit codes: 0 dispatched, or nothing pending | 1 Codex reported failure
#             2 usage / missing python3 or codex
#             3 read-only invariant violated (propagated from delegate.sh)
set -uo pipefail

ROOT_DIR="$(pwd)"
QUEUE="${CODEX_QUEUE_FILE:-$ROOT_DIR/memory/codex-queue.jsonl}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat >&2 <<'USAGE'
usage: dispatch.sh (--list | --next | --id <ID>)
USAGE
}

MODE=""
TARGET_ID=""
case "${1:-}" in
  --list) MODE="list" ;;
  --next) MODE="next" ;;
  --id)   MODE="id"; TARGET_ID="${2:-}"; [[ -n "$TARGET_ID" ]] || { usage; exit 2; } ;;
  -h|--help) usage; exit 0 ;;
  *) usage; exit 2 ;;
esac

if [[ ! -f "$QUEUE" ]]; then
  echo "dispatch.sh: no queue file at $QUEUE -- run discover.sh first" >&2
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "dispatch.sh: python3 is required" >&2
  exit 2
fi

if [[ "$MODE" == "list" ]]; then
  QUEUE="$QUEUE" python3 - <<'PY'
import json, os
count = 0
for line in open(os.environ["QUEUE"], encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    e = json.loads(line)
    if e.get("status") == "pending":
        count += 1
        print(f"{e['id']}  {e['file']}:{e['line']}  {e['claim'][:70]}")
print(f"-- {count} pending")
PY
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "dispatch.sh: codex is not on PATH -- verify this claim yourself" >&2
  exit 2
fi

SELECTED_TSV="$(QUEUE="$QUEUE" MODE="$MODE" TARGET_ID="$TARGET_ID" python3 - <<'PY'
import json, os
mode = os.environ["MODE"]
target_id = os.environ.get("TARGET_ID", "")
entries = []
with open(os.environ["QUEUE"], encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

picked = None
if mode == "next":
    for e in entries:
        if e.get("status") == "pending":
            picked = e
            break
elif mode == "id":
    for e in entries:
        if e.get("id") == target_id:
            picked = e
            break

if picked:
    print(f"{picked['id']}\t{picked['file']}\t{picked['line']}\t{picked['claim']}")
PY
)"

if [[ -z "$SELECTED_TSV" ]]; then
  echo "dispatch.sh: nothing to dispatch"
  exit 0
fi

# claim text is last so it absorbs anything past the 3rd tab, in case it
# ever contained one.
IFS=$'\t' read -r CLAIM_ID CLAIM_FILE CLAIM_LINE CLAIM_TEXT <<< "$SELECTED_TSV"

echo "dispatching: $CLAIM_FILE:$CLAIM_LINE"
echo "  claim: $CLAIM_TEXT"

TASK="$(cat <<TASKEOF
[目的] 次の主張がコードの実装で成立しているかを確認する。判断ではなく事実の照合をせよ。
[主張] $CLAIM_TEXT
[主張の出典] $CLAIM_FILE:$CLAIM_LINE
[対象] リポジトリ全体のうち、主張に関係する経路のみ
[反証条件] 成立していなければ「成立していない」と明言し、反する箇所を示せ。
           成立していることを無理に示そうとするな。
[報告] 確認した箇所は path:line で示せ
TASKEOF
)"

set +e
REPORT="$("$SCRIPT_DIR/delegate.sh" --label "verify-$CLAIM_ID" "$TASK")"
DELEGATE_EXIT=$?
set -e 2>/dev/null || true

if [[ "$DELEGATE_EXIT" -eq 3 ]]; then
  echo "dispatch.sh: delegate.sh reported a read-only violation -- queue left untouched" >&2
  exit 3
fi

QUEUE="$QUEUE" CLAIM_ID="$CLAIM_ID" REPORT="$REPORT" DELEGATE_EXIT="$DELEGATE_EXIT" python3 - <<'PY'
import json, os

queue_path = os.environ["QUEUE"]
claim_id = os.environ["CLAIM_ID"]
delegate_exit = os.environ["DELEGATE_EXIT"]

try:
    report = json.loads(os.environ["REPORT"])
except json.JSONDecodeError:
    report = None

entries = []
with open(queue_path, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

updated = None
for e in entries:
    if e["id"] != claim_id:
        continue
    if delegate_exit != "0" or report is None:
        e["status"] = "delegation_failed"
    else:
        claims = ((report.get("report") or {}).get("claims")) or []
        verdict = claims[0]["status"] if claims else "uncertain"
        e["status"] = verdict if verdict in ("confirmed", "falsified") else "uncertain"
        e["evidence"] = claims[0]["evidence"] if claims else (report.get("report") or {}).get("summary")
    updated = e

with open(queue_path, "w", encoding="utf-8") as fh:
    for e in entries:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

if updated:
    print(f"result: {updated['status']}")
    if updated.get("evidence"):
        print(f"evidence: {updated['evidence']}")
PY

exit "$DELEGATE_EXIT"
