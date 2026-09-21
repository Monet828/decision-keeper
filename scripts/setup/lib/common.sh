#!/usr/bin/env bash

# Hard-required paths: if any of these is missing, doctor.sh treats the
# project as broken (non-zero exit). Kept to structurally load-bearing
# items only -- the memory/ state-externalization files, the canonical
# rules docs, and the scripts that onboarding/memory-writing depend on.
required_paths=(
  "AGENTS.md"
  "CLAUDE.md"
  "app"
  "memory/current-state.md"
  "memory/decisions.md"
  "memory/tasks.md"
  "memory/sessions"
  "scripts/setup/doctor.sh"
  "scripts/setup/bootstrap.sh"
  "scripts/hooks/save-memory.sh"
)

# Soft/optional paths: missing is worth flagging, but does not fail doctor.sh.
# These are opt-in-by-nature areas (DB usage, shared-lib splitting, reusable
# skills/patterns, tests not yet written).
warn_paths=(
  "app/README.md"
  "docs/adr"
  "skills"
  "assets/patterns"
  "src"
  "tests"
)

root_project_markers=(
  "package.json"
  "pyproject.toml"
  "Cargo.toml"
  "go.mod"
  "Gemfile"
)

app_project_markers=(
  "app/package.json"
  "app/pyproject.toml"
  "app/Cargo.toml"
  "app/go.mod"
  "app/Gemfile"
  "app/requirements.txt"
  "app/next.config.ts"
  "app/next.config.js"
  "app/vercel.json"
)

# Emits one line per path in required_paths/warn_paths as tab-separated
# "path<TAB>status<TAB>severity" (status: ok|missing, severity: error|warning).
# This is the single canonical check pass -- both doctor.sh's human-readable
# output and its --json output are rendered from these same lines, so they
# can never disagree with each other.
collect_path_checks() {
  local root_dir="$1"
  local path
  for path in "${required_paths[@]}"; do
    if [[ -e "$root_dir/$path" ]]; then
      printf '%s\tok\terror\n' "$path"
    else
      printf '%s\tmissing\terror\n' "$path"
    fi
  done
  for path in "${warn_paths[@]}"; do
    if [[ -e "$root_dir/$path" ]]; then
      printf '%s\tok\twarning\n' "$path"
    else
      printf '%s\tmissing\twarning\n' "$path"
    fi
  done
}

# Back-compat plain printer (used by bootstrap.sh's onboarding summary,
# which is informational only and does not gate on exit code).
print_required_paths() {
  local root_dir="$1"
  local path
  for path in "${required_paths[@]}" "${warn_paths[@]}"; do
    if [[ -e "$root_dir/$path" ]]; then
      echo "[ok] $path"
    else
      echo "[missing] $path"
    fi
  done
}

print_root_project_markers() {
  local root_dir="$1"
  local found=false
  for marker in "${root_project_markers[@]}"; do
    if [[ -f "$root_dir/$marker" ]]; then
      echo "[detected] $marker"
      found=true
    fi
  done
  if [[ "$found" == false ]]; then
    echo "[info] no common root project manifest detected"
  fi
}

print_app_project_markers() {
  local root_dir="$1"
  local found=false
  for marker in "${app_project_markers[@]}"; do
    if [[ -f "$root_dir/$marker" ]]; then
      echo "[detected] $marker"
      found=true
    fi
  done
  if [[ "$found" == false ]]; then
    echo "[info] no common app manifest detected under app/"
  fi
}
