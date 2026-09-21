#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Run Template Harness =="
"$ROOT_DIR/install.sh"
"$ROOT_DIR/scripts/hooks/pre-task.sh"
echo
"$ROOT_DIR/scripts/setup/bootstrap.sh"
