#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Install Template =="
required_dirs=(
  "agents"
  "app"
  "assets/patterns"
  "docs/adr"
  "memory/sessions"
  "skills"
  "scripts/hooks"
  "scripts/loop"
  "scripts/setup"
  "src"
  "tests"
)

for dir in "${required_dirs[@]}"; do
  mkdir -p "$ROOT_DIR/$dir"
done

echo "Template directories are ready."
echo "Run ./scripts/setup/doctor.sh to inspect the project."
