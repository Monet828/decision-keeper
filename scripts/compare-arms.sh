#!/usr/bin/env bash
# 両群の差を、自己申告ではなく git と実行結果から測る。
# 使い方: ./scripts/compare-arms.sh <base-commit>
set -uo pipefail

BASE="${1:-a17ce40}"
NO_ASSET=/tmp/dk/wt/no-asset
WITH_ASSET=/tmp/dk/wt/with-asset

measure() {
  local wt="$1" label="$2"
  echo "## ${label}"
  echo
  if [[ ! -d "$wt" ]]; then echo "  作業ツリーが無い"; return; fi

  local changed added removed
  changed=$(git -C "$wt" diff --name-only "$BASE" | grep -c . || true)
  added=$(git -C "$wt" diff --numstat "$BASE" | awk '{s+=$1} END{print s+0}')
  removed=$(git -C "$wt" diff --numstat "$BASE" | awk '{s+=$2} END{print s+0}')
  echo "- 変更ファイル数: ${changed}"
  echo "- 追加行 / 削除行: ${added} / ${removed}"

  echo "- 変更したファイル:"
  git -C "$wt" diff --name-only "$BASE" | sed 's/^/    - /' || true

  local newfiles
  newfiles=$(git -C "$wt" status --porcelain | grep '^??' | sed 's/^?? //' | grep -v 'node_modules' || true)
  if [[ -n "$newfiles" ]]; then
    echo "- 新規ファイル:"
    while IFS= read -r f; do printf '    - %s\n' "$f"; done <<< "$newfiles"
  fi

  # 仕様書を先に更新したか（仕様書駆動ルールの遵守）
  if git -C "$wt" diff --name-only "$BASE" | grep -q '^docs/'; then
    echo "- 仕様書の更新: あり"
  else
    echo "- 仕様書の更新: **なし**（このリポジトリの絶対ルールに違反）"
  fi

  # 検証
  echo "- 検証:"
  if (cd "$wt" && npm run typecheck >/dev/null 2>&1); then
    echo "    - typecheck: 通過"
  else
    echo "    - typecheck: **失敗**"
  fi

  local total fail
  read -r total fail < <(cd "$wt" && npm test 2>&1 | awk '/^ℹ tests/{t=$3} /^ℹ fail/{f=$3} END{print t" "f}')
  echo "    - npm test: ${total:-?} 件中 ${fail:-?} 件失敗（着手前は 1904 件中 4 件失敗）"

  echo
}

echo "# 両群の比較（機械観測）"
echo
echo "共通の出発点: \`${BASE}\`"
echo
measure "$NO_ASSET" "資産なし群"
measure "$WITH_ASSET" "資産あり群"

echo "## 差分そのものの比較"
echo
if [[ -d "$NO_ASSET" && -d "$WITH_ASSET" ]]; then
  a=$(git -C "$NO_ASSET" diff --name-only "$BASE" | sort)
  b=$(git -C "$WITH_ASSET" diff --name-only "$BASE" | sort)
  echo "- 両群が共通で触ったファイル:"
  comm -12 <(echo "$a") <(echo "$b") | sed 's/^/    - /' || true
  echo "- 資産なし群だけが触ったファイル:"
  comm -23 <(echo "$a") <(echo "$b") | sed 's/^/    - /' || true
  echo "- 資産あり群だけが触ったファイル:"
  comm -13 <(echo "$a") <(echo "$b") | sed 's/^/    - /' || true
fi
