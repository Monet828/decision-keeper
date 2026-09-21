#!/usr/bin/env bash
#
# install-hooks.sh — scripts/hooks/ 内の git フックを .git/hooks/ に導入する。
#
# scaffold / setup から呼び出して使う想定。既存フックがあればバックアップを取る。
# シンボリックリンクを優先し、リンクできない環境ではコピーにフォールバックする。
#
set -eu

# このスクリプトのあるディレクトリ = フック配布元。
HOOKS_SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# リポジトリの .git/hooks を解決（worktree でも動くよう git に問い合わせる）。
GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || true)"
if [ -z "${GIT_DIR}" ]; then
  echo "エラー: git リポジトリ内で実行してください。" >&2
  exit 1
fi
HOOKS_DST_DIR="${GIT_DIR}/hooks"
mkdir -p "${HOOKS_DST_DIR}"

# 導入対象のフック（install-hooks.sh 自身は除外）。
HOOKS="pre-push"

for hook in ${HOOKS}; do
  src="${HOOKS_SRC_DIR}/${hook}"
  dst="${HOOKS_DST_DIR}/${hook}"

  if [ ! -f "${src}" ]; then
    echo "警告: ${src} が見つかりません。スキップします。" >&2
    continue
  fi

  # 既存フックのバックアップ（シンボリックリンクは除く）。
  if [ -e "${dst}" ] && [ ! -L "${dst}" ]; then
    mv "${dst}" "${dst}.backup.$(date +%Y%m%d%H%M%S)"
    echo "既存の ${hook} を退避しました。"
  fi

  # シンボリックリンクを試み、失敗したらコピー。
  rm -f "${dst}"
  if ln -s "${src}" "${dst}" 2>/dev/null; then
    echo "リンク: ${dst} -> ${src}"
  else
    cp "${src}" "${dst}"
    echo "コピー: ${src} -> ${dst}"
  fi

  chmod +x "${dst}" 2>/dev/null || true
  chmod +x "${src}" 2>/dev/null || true
done

echo "git フックの導入が完了しました。"
