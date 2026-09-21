# Memory Guide

`memory/` は作業記憶であり、正式仕様の正本ではない。

## 使い分け

ディレクトリ全体の役割は `docs/project-structure.md` を唯一の正として参照する。

- `current-state.md`
  - 今いまの真実、作業中の論点、短期的な注意点を書く
- `decisions.md`
  - 次回以降も参照される設計判断や運用判断を書く
- `tasks.md`
  - 未完了タスク、優先度、状態を管理する
- `sessions/`
  - 日ごとの作業ログ、Goal / Scope / Stop Conditions、Loop State、Unresolved / Open Questions、Resume From、途中メモを残す
- `codex-queue.jsonl`
  - `scripts/codex/discover.sh` / `dispatch.sh` の状態。人間が編集する場所ではない。
    詳細は `skills/delegating-to-codex/SKILL.md` §9

## 昇格の目安

- 長期的に有効な内容は `docs/` または `docs/adr/` へ昇格する
- 一時的な前提や途中メモは `memory/` に留める

## 最初に見る順番

1. `current-state.md`
2. 関連する `docs/`
3. `decisions.md`
4. `tasks.md`
5. 必要なら `sessions/`

## Loop Engineering v1

session に以下がある場合は、最優先で確認する。

- `Loop State`
- `Unresolved / Open Questions`
- `Resume From`

再開時の基本順序:

1. `current-state.md`
2. 当日または最新の `sessions/`
3. `Resume From`
4. 関連する `docs/`
