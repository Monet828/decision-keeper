#!/usr/bin/env bash
set -euo pipefail

# Spec-First Development
# 雛形と運用ルール: docs/templates/spec.md
# 対話手順: skills/authoring-specs/SKILL.md

ROOT_DIR="$(pwd)"
SPECS="$ROOT_DIR/docs/specs"
APPROVALS="$ROOT_DIR/docs/approvals"
TPL="$ROOT_DIR/docs/templates"

usage() {
  cat <<'EOF'
usage: spec-first.sh <command>

  new-spec <name>   仕様の雛形を作る（docs/specs/<name>.md）
  status            仕様と承認の対応、ハッシュ照合
  unlinked [base]   要件IDを持たない変更ファイルを列挙
  check             status + unlinked + 点検項目
EOF
}

# ---- 仕様ごとの承認記録を読む ------------------------------------------
approval_hash() { # $1=name
  local f="$APPROVALS/$1.md"
  [[ -f "$f" ]] || return 1
  grep -oE '\b[0-9a-f]{7,40}\b' "$f" | head -1
}

cmd_new_spec() {
  local name="${1:-}"
  [[ -z "$name" ]] && { usage; exit 1; }
  # **名前を検証する。** しないと `new-spec --help` が `--help` という名前の
  # 仕様を作る（実測でそうなった）。ファイル名になるので文字も絞る。
  if ! [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]]; then
    echo "仕様名は英数字で始まり、英数字・ハイフン・アンダースコアのみ: $name" >&2
    exit 1
  fi
  mkdir -p "$SPECS" "$APPROVALS"
  local dest="$SPECS/$name.md"
  [[ -e "$dest" ]] && { echo "既にある: $dest"; exit 1; }
  [[ -e "$SPECS/$name" ]] && { echo "既にある: $SPECS/$name"; exit 1; }
  local today; today="$(date '+%Y-%m-%d')"

  sed "s/YYYY-MM-DD/$today/; s|<この仕様が扱うもの>|$name|; s|<name>|$name|g" \
    "$TPL/spec.md" > "$dest"
  echo "作った: $dest"

  sed "s|<仕様名>|$name|; s|<name>|$name|g" \
    "$APPROVALS/_TEMPLATE.md" > "$APPROVALS/$name.md"
  echo "作った: $APPROVALS/$name.md"
  echo
  echo "次にやること:"
  echo "  1. §1 と §2 を書く（作る理由が書けないなら、作らなくてよい）"
  echo "  2. §3 に作らないものを書く。ここが空の仕様は膨張する"
  echo "  3. 要件に確認方法を付ける。書けない要件は要件として成立していない"
  echo "  4. 全行に [確定]/[候補]/[未定] を付ける"
  echo "  5. コミットしてから承認を求める（ハッシュが要る）"
}

cmd_status() {
  echo "== 仕様と承認 =="
  local any=0
  # 単一ファイル（docs/specs/<name>.md）と、旧いディレクトリ形式の両方を見る
  local entries=()
  for f in "$SPECS"/*.md; do [[ -f "$f" ]] && entries+=("$f"); done
  for d in "$SPECS"/*/; do [[ -d "$d" ]] && entries+=("${d%/}"); done
  for e in "${entries[@]:-}"; do
    [[ -e "$e" ]] || continue
    any=1
    local name spec=""
    if [[ -f "$e" ]]; then
      name="$(basename "$e" .md)"; spec="$e"
    else
      name="$(basename "$e")"
      for cand in "$e/spec.md" "$e/requirements.md"; do
        [[ -f "$cand" ]] && { spec="$cand"; break; }
      done
    fi
    local rel="${spec#"$ROOT_DIR"/}"
    printf "  %-34s %s\n" "$name" "${rel:-（仕様ファイル無し）}"

    if ! [[ -f "$APPROVALS/$name.md" ]]; then
      echo "      承認記録なし → 実装に入らない"
      continue
    fi
    local h; h="$(approval_hash "$name" || true)"
    if [[ -z "$h" ]]; then
      echo "      承認記録にハッシュなし → 照合できない。コミットしてから承認を求める"
      continue
    fi
    if [[ -n "${spec:-}" ]] && git -C "$ROOT_DIR" rev-parse --verify "$h" >/dev/null 2>&1; then
      if git -C "$ROOT_DIR" diff --quiet "$h" -- "$spec" 2>/dev/null; then
        echo "      承認済み ($h) 仕様は承認時から変わっていない"
      else
        echo "      ⚠ 承認後に仕様が変わっている ($h) → 実装を止めて再承認を求める"
      fi
    else
      echo "      ハッシュ $h が見つからない → 照合できない"
    fi
  done
  if [[ "$any" == "0" ]]; then echo "  （仕様なし）"; fi
}

cmd_unlinked() {
  local base="${1:-HEAD}"
  echo "== 要件IDを持たない変更ファイル（REQ-B08） =="
  echo "  基準: $base"
  local files found=0
  files="$(git -C "$ROOT_DIR" diff --name-only "$base" 2>/dev/null || true)"
  [[ -z "$files" ]] && files="$(git -C "$ROOT_DIR" diff --name-only --cached 2>/dev/null || true)"
  if [[ -z "$files" ]]; then
    echo "  変更なし"
    return
  fi
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    [[ -f "$ROOT_DIR/$f" ]] || continue
    case "$f" in
      docs/*|memory/*|*.md|*.json|*.yml|*.yaml|*.lock|*.txt) continue ;;
    esac
    if ! grep -qE 'R-[0-9]+|REQ-[A-Za-z]*[0-9]+|§[0-9]+' "$ROOT_DIR/$f" 2>/dev/null; then
      echo "  要確認: $f"
      found=$((found + 1))
    fi
  done <<< "$files"
  if [[ "$found" == "0" ]]; then
    echo "  なし"
  else
    echo
    echo "  ※ これは「未達」ではなく「要確認」。設定や自動生成物など、"
    echo "     要件に紐づかないのが正しいものもある。"
    echo "  ※ IDは書けば通る。防げるのは書き忘れであって偽装ではない。"
  fi
}

case "${1:-check}" in
  new-spec) shift; cmd_new_spec "$@" ;;
  status)   cmd_status ;;
  unlinked) shift; cmd_unlinked "${1:-HEAD}" ;;
  check)
    cmd_status; echo; cmd_unlinked "HEAD"
    cat <<'EOF'

点検:
- 承認記録にコミットハッシュがあるか
- 全行に [確定]/[候補]/[未定] が付いているか
- 要件に「確認方法」が書かれているか
- §8 の未定に「止まる作業」が書かれているか
- 実装中に要件が変わったなら、変更履歴に種別つきで記録したか
EOF
    ;;
  -h|--help|help) usage ;;
  *) usage; exit 1 ;;
esac
