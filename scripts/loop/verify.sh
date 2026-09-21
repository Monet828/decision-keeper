#!/usr/bin/env bash
set -uo pipefail
# Intentionally not `set -e`: every configured check must run even if an
# earlier one fails, so this script can report a complete PASS/SKIP/FAIL
# summary and the correct aggregate exit code.
#
# This is a real verification runner: it detects what's actually configured
# in the project (pyproject.toml, package.json, Cargo.toml, go.mod, *.sh)
# and runs only those checks. It never invents usage of a tool that isn't
# configured, and never treats a missing command as a pass.
#
# For the older behavior of this script -- a review checklist plus an
# interactive self-reported summary appended to the session log -- see
# ./record-verification.sh, which now owns that job under its own name.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR" || exit 1

RAN=0
FAILED=0

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; FAILED=$((FAILED + 1)); }
skip() { echo "[SKIP] $1: $2"; }

# ---- Shell: syntax + shellcheck (always relevant, every generated project ships *.sh) ----
sh_files=()
while IFS= read -r f; do
  sh_files+=("$f")
done < <(find . -type f -name '*.sh' \
  -not -path './.git/*' \
  -not -path './node_modules/*' \
  -not -path '*/node_modules/*' \
  2>/dev/null | sort)

if [[ "${#sh_files[@]}" -eq 0 ]]; then
  skip "shell syntax" "no .sh files found"
  skip "shellcheck" "no .sh files found"
else
  RAN=$((RAN + 1))
  syntax_ok=true
  for f in "${sh_files[@]:-}"; do
    [[ -z "$f" ]] && continue
    if ! bash -n "$f"; then
      syntax_ok=false
    fi
  done
  if [[ "$syntax_ok" == true ]]; then
    pass "shell syntax"
  else
    fail "shell syntax"
  fi

  if command -v shellcheck >/dev/null 2>&1; then
    RAN=$((RAN + 1))
    shellcheck_ok=true
    for f in "${sh_files[@]:-}"; do
      [[ -z "$f" ]] && continue
      if ! shellcheck "$f"; then
        shellcheck_ok=false
      fi
    done
    if [[ "$shellcheck_ok" == true ]]; then
      pass "shellcheck"
    else
      fail "shellcheck"
    fi
  else
    skip "shellcheck" "not installed"
  fi
fi

# ---- Python (pyproject.toml) ----
if [[ -f "pyproject.toml" ]]; then
  if command -v pytest >/dev/null 2>&1; then
    RAN=$((RAN + 1))
    if pytest >/dev/null 2>&1; then pass "pytest"; else fail "pytest"; fi
  else
    skip "pytest" "pyproject.toml present but pytest is not installed"
  fi

  if grep -q '^\[tool\.ruff\]' pyproject.toml 2>/dev/null; then
    if command -v ruff >/dev/null 2>&1; then
      RAN=$((RAN + 1))
      if ruff check . >/dev/null 2>&1; then pass "ruff"; else fail "ruff"; fi
    else
      skip "ruff" "configured in pyproject.toml but ruff is not installed"
    fi
  else
    skip "ruff" "not configured"
  fi

  if grep -q '^\[tool\.mypy\]' pyproject.toml 2>/dev/null; then
    if command -v mypy >/dev/null 2>&1; then
      RAN=$((RAN + 1))
      if mypy . >/dev/null 2>&1; then pass "mypy"; else fail "mypy"; fi
    else
      skip "mypy" "configured in pyproject.toml but mypy is not installed"
    fi
  else
    skip "mypy" "not configured"
  fi
else
  skip "pytest" "no pyproject.toml"
  skip "ruff" "no pyproject.toml"
  skip "mypy" "no pyproject.toml"
fi

# ---- Node (package.json, checked at repo root and under app/) ----
check_npm_project() {
  local dir="$1"
  local label_suffix="$2"
  local pkg="$dir/package.json"

  if [[ ! -f "$pkg" ]]; then
    skip "npm test$label_suffix" "no $pkg"
    skip "npm lint$label_suffix" "no $pkg"
    skip "npm build$label_suffix" "no $pkg"
    return
  fi

  if ! command -v npm >/dev/null 2>&1; then
    skip "npm test$label_suffix" "$pkg present but npm is not installed"
    skip "npm lint$label_suffix" "$pkg present but npm is not installed"
    skip "npm build$label_suffix" "$pkg present but npm is not installed"
    return
  fi

  local script_name
  for script_name in test lint build; do
    local script_value
    script_value="$(sed -n "s/.*\"$script_name\"[[:space:]]*:[[:space:]]*\"\\(.*\\)\".*/\\1/p" "$pkg" | head -1)"
    if [[ -z "$script_value" ]]; then
      skip "npm $script_name$label_suffix" "not configured"
    elif [[ "$script_value" == *"no test specified"* ]]; then
      skip "npm $script_name$label_suffix" "placeholder script, nothing real configured"
    else
      RAN=$((RAN + 1))
      if ( cd "$dir" && npm run "$script_name" >/dev/null 2>&1 ); then
        pass "npm $script_name$label_suffix"
      else
        fail "npm $script_name$label_suffix"
      fi
    fi
  done
}

check_npm_project "." ""
if [[ -d "app" ]]; then
  check_npm_project "app" " (app/)"
fi

# ---- Rust (Cargo.toml) ----
if [[ -f "Cargo.toml" ]]; then
  if command -v cargo >/dev/null 2>&1; then
    RAN=$((RAN + 1))
    if cargo test >/dev/null 2>&1; then pass "cargo test"; else fail "cargo test"; fi
    RAN=$((RAN + 1))
    if cargo clippy >/dev/null 2>&1; then pass "cargo clippy"; else fail "cargo clippy"; fi
  else
    skip "cargo test" "Cargo.toml present but cargo is not installed"
    skip "cargo clippy" "Cargo.toml present but cargo is not installed"
  fi
else
  skip "cargo test" "no Cargo.toml"
  skip "cargo clippy" "no Cargo.toml"
fi

# ---- Go (go.mod) ----
if [[ -f "go.mod" ]]; then
  if command -v go >/dev/null 2>&1; then
    RAN=$((RAN + 1))
    if go test ./... >/dev/null 2>&1; then pass "go test"; else fail "go test"; fi
  else
    skip "go test" "go.mod present but go is not installed"
  fi
else
  skip "go test" "no go.mod"
fi

echo
echo "== Summary =="
echo "ran: $RAN, failed: $FAILED"

if [[ "$FAILED" -gt 0 ]]; then
  exit 1
fi
exit 0
