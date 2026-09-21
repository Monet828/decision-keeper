#!/usr/bin/env bash
# Find claims marked for periodic verification and queue new ones for
# scripts/codex/dispatch.sh. Never calls Codex -- this is the "patrol" half
# of the two-layer design: a low-frequency scan that surfaces candidates,
# and a human-triggered dispatch that decides whether to spend quota on them.
# See skills/delegating-to-codex/SKILL.md section 9.
#
# Marker convention: an HTML comment directly before the claim.
#
#   <!-- codex:verify -->
#   `security.ts` に集約し、3箇所で判定ロジックを重複させない
#
# A claim's id hashes (file path + claim text). Editing the claim text
# produces a new id and re-queues it; an unchanged, already-handled claim is
# never queued twice -- discover.sh is safe to run on every patrol tick.
#
#   ./scripts/codex/discover.sh                  # scan the defaults below
#   ./scripts/codex/discover.sh README.md docs    # scan specific paths
#
# Exit codes: 0 always. A scan finding zero new candidates is not a failure.
set -uo pipefail

ROOT_DIR="$(pwd)"
QUEUE="${CODEX_QUEUE_FILE:-$ROOT_DIR/memory/codex-queue.jsonl}"
mkdir -p "$(dirname "$QUEUE")"
touch "$QUEUE"

if ! command -v python3 >/dev/null 2>&1; then
  echo "discover.sh: python3 is required -- skipping scan" >&2
  exit 0
fi

TARGETS=("$@")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(README.md AGENTS.md CLAUDE.md docs)
fi

EXISTING_TARGETS=()
for target in "${TARGETS[@]}"; do
  [[ -e "$ROOT_DIR/$target" ]] && EXISTING_TARGETS+=("$ROOT_DIR/$target")
done

MATCHES_FILE="$(mktemp)"
trap 'rm -f "$MATCHES_FILE"' EXIT

if [[ ${#EXISTING_TARGETS[@]} -gt 0 ]]; then
  # -F: the marker has no regex metacharacters and treating it as fixed
  # string avoids any surprise if it ever does.
  grep -rn --include='*.md' -F 'codex:verify' "${EXISTING_TARGETS[@]}" 2>/dev/null > "$MATCHES_FILE" || true
fi

QUEUE="$QUEUE" MATCHES_FILE="$MATCHES_FILE" ROOT_DIR="$ROOT_DIR" python3 - <<'PY'
import hashlib, json, os

root = os.environ["ROOT_DIR"]
queue_path = os.environ["QUEUE"]
matches_path = os.environ["MATCHES_FILE"]
MARKER = "codex:verify"

existing_ids = set()
with open(queue_path, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            existing_ids.add(json.loads(line)["id"])
        except Exception:
            continue

new_entries = []
seen_this_run = set()

with open(matches_path, encoding="utf-8") as fh:
    for row in fh:
        row = row.rstrip("\n")
        if not row:
            continue
        # grep -n output: path:lineno:content -- content may itself contain
        # colons, so split only on the first two.
        try:
            file_path, rest = row.split(":", 1)
            lineno_str, _content = rest.split(":", 1)
            lineno = int(lineno_str)
        except ValueError:
            continue

        rel = os.path.relpath(file_path, root)
        with open(file_path, encoding="utf-8", errors="replace") as source:
            lines = source.readlines()

        # The claim is the run of non-blank lines immediately after the
        # marker (up to 5 lines), so a claim can wrap without a second
        # marker. It stops at a blank line OR the next marker -- markers are
        # often adjacent with no blank line between list items, and without
        # this check a claim would swallow the next marker plus the start of
        # the next claim (found by running this against a real densely
        # bulleted README, not by unit-testing in isolation).
        claim_lines = []
        for candidate in lines[lineno:lineno + 5]:
            text = candidate.strip()
            if MARKER in text:
                break
            if not text:
                if claim_lines:
                    break
                continue
            claim_lines.append(text)
        claim = " ".join(claim_lines).strip()
        if not claim:
            continue

        claim_id = hashlib.sha256(f"{rel}:{claim}".encode("utf-8")).hexdigest()[:16]
        if claim_id in existing_ids or claim_id in seen_this_run:
            continue
        seen_this_run.add(claim_id)
        new_entries.append({
            "id": claim_id,
            "file": rel,
            "line": lineno + 1,
            "claim": claim,
            "status": "pending",
        })

if new_entries:
    with open(queue_path, "a", encoding="utf-8") as fh:
        for entry in new_entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

print(f"discover.sh: {len(new_entries)} new candidate(s) -- queue: {queue_path}")
for entry in new_entries:
    print(f"  + {entry['file']}:{entry['line']}  {entry['claim'][:70]}")
PY
