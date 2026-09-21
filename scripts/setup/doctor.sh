#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMMON_LIB="$ROOT_DIR/scripts/setup/lib/common.sh"

# shellcheck source=/dev/null
source "$COMMON_LIB"

usage() {
  cat <<EOF
Usage:
  ./scripts/setup/doctor.sh [--json]

Exit code: 0 if no required path is missing, 1 otherwise.
Warnings (optional/soft paths) never affect the exit code.
EOF
}

JSON_MODE=false
for arg in "$@"; do
  case "$arg" in
    --json)
      JSON_MODE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown option: $arg" >&2
      usage
      exit 1
      ;;
  esac
done

check_file() {
  local path="$1"
  if [[ -e "$ROOT_DIR/$path" ]]; then
    echo "[ok] $path"
  else
    echo "[missing] $path"
  fi
}

# Single canonical check pass: both renderers below read from this same
# array, so human output and --json output can never disagree.
path_check_lines=()
while IFS= read -r line; do
  path_check_lines+=("$line")
done < <(collect_path_checks "$ROOT_DIR")

passed=0
warnings=0
errors=0
for line in "${path_check_lines[@]}"; do
  IFS=$'\t' read -r _ status severity <<< "$line"
  if [[ "$status" == "ok" ]]; then
    passed=$((passed + 1))
  elif [[ "$severity" == "error" ]]; then
    errors=$((errors + 1))
  else
    warnings=$((warnings + 1))
  fi
done

if [[ "$JSON_MODE" == true ]]; then
  # JSON mode: nothing but the JSON object goes to stdout.
  if [[ "$errors" -gt 0 ]]; then
    overall_status="fail"
  elif [[ "$warnings" -gt 0 ]]; then
    overall_status="warn"
  else
    overall_status="ok"
  fi

  json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
  }

  checks_json=""
  for line in "${path_check_lines[@]}"; do
    IFS=$'\t' read -r path status severity <<< "$line"
    entry="{\"path\":\"$(json_escape "$path")\",\"status\":\"$status\",\"severity\":\"$severity\"}"
    if [[ -z "$checks_json" ]]; then
      checks_json="$entry"
    else
      checks_json="$checks_json,$entry"
    fi
  done

  printf '{"status":"%s","passed":%d,"warnings":%d,"errors":%d,"checks":[%s]}\n' \
    "$overall_status" "$passed" "$warnings" "$errors" "$checks_json"
else
  echo "== AI Project Doctor =="
  echo "root: $ROOT_DIR"
  echo

  echo "== Required Paths =="
  for line in "${path_check_lines[@]}"; do
    IFS=$'\t' read -r path status severity <<< "$line"
    if [[ "$status" == "ok" ]]; then
      echo "[ok] $path"
    elif [[ "$severity" == "error" ]]; then
      echo "[missing] $path (required)"
    else
      echo "[missing] $path (optional)"
    fi
  done

  echo
  echo "== Root Manifests =="
  print_root_project_markers "$ROOT_DIR"

  echo
  echo "== app/ Manifests =="
  print_app_project_markers "$ROOT_DIR"

  echo
  echo "== Environment Files =="
  env_found=false
  for file in .env .env.local .env.example .env.development .env.production app/.env app/.env.local app/.env.example app/.env.development app/.env.production; do
    if [[ -f "$ROOT_DIR/$file" ]]; then
      echo "[ok] $file"
      env_found=true
    fi
  done
  if [[ "$env_found" == false ]]; then
    echo "[info] no root or app env files detected"
  fi

  echo
  echo "== Optional Slide Assets =="
  if [[ -d "$ROOT_DIR/assets/slides" ]]; then
    check_file "assets/slides/SLIDE-md"
    check_file "assets/slides/SLIDE-PATTERN"
  else
    echo "[info] slide pack not installed"
  fi

  echo
  echo "== Optional Pattern Template =="
  if [[ -f "$ROOT_DIR/assets/patterns/PATTERN-TEMPLATE.md" ]]; then
    check_file "assets/patterns/PATTERN-TEMPLATE.md"
  else
    echo "[info] no pattern template installed"
  fi

  echo
  echo "== Session Freshness =="
  latest_session="$(find "$ROOT_DIR/memory/sessions" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort | tail -n 1 || true)"
  if [[ -n "$latest_session" ]]; then
    echo "[latest] ${latest_session#"$ROOT_DIR"/}"
  else
    echo "[info] no session markdown files found"
  fi

  echo
  echo "== Git Status =="
  if [[ -d "$ROOT_DIR/.git" ]]; then
    git -C "$ROOT_DIR" status --short || true
  else
    echo "[info] no .git directory detected"
  fi

  echo
  echo "== Summary =="
  echo "passed: $passed, warnings: $warnings, errors: $errors"
fi

if [[ "$errors" -gt 0 ]]; then
  exit 1
fi
exit 0
