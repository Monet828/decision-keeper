#!/usr/bin/env bash
set -euo pipefail

echo "== Stop Boundary =="
echo "Pause and ask for confirmation if one of these is true:"
echo "- scope expansion is required"
echo "- a new specification decision is needed"
echo "- destructive or irreversible action is required"
echo "- prod/auth/billing/secrets are affected"
echo "- you cannot verify the result safely"
echo
echo "If stopping, record the boundary in ./scripts/hooks/save-memory.sh"
