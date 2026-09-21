#!/usr/bin/env bash
set -euo pipefail

echo "== Post Task =="
echo "Review:"
echo "- changed files"
echo "- tests actually run"
echo "- decision candidates"
echo "- memory/docs updates"
echo "- whether verifier has run"
echo "- whether Resume From should be updated"
echo
echo "Recommended next steps: ./scripts/loop/verify.sh then ./scripts/hooks/save-memory.sh"
