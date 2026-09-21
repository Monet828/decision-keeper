# Loop Engineering v1

このドキュメントは、`AI_dev_template` における最小の loop engineering 運用を説明する。

## 目的

- 合意済みゴールの中では止まりにくくする
- ただし暴走しにくくする
- 次回セッションで再開しやすくする

## 基本 loop

1. `pre-task.sh`
2. `bootstrap.sh`
3. execute
4. `stop.sh` で境界確認
5. `verify.sh`（実チェック）→ `record-verification.sh`（結果と所感の記録）
6. `save-memory.sh`
7. done or blocked

## session に残すもの

- Goal
- Scope
- Out of Scope
- Stop Conditions
- Loop State
- Unresolved / Open Questions
- Resume From

## Loop State

推奨 state:

- `goal_defined`
- `context_loaded`
- `plan_selected`
- `execute`
- `verify`
- `checkpoint`
- `done`
- `blocked`

## Resume From

少なくとも以下を残す。

- `next_state`
- `required_context`
- `blocking_reason`

## 未確定事項

- 後で判断する論点は `Unresolved / Open Questions` に残す
- 次回見落とすと危険な場合は `current-state.md` や `tasks.md` に昇格する

## verifier の位置づけ

- 完了前に最低 1 回通す
- 実行した確認と、未確認の点を分ける
- テスト未実行なら、それを明示する

## この v1 でやらないこと

- 複雑な multi-agent orchestration
- queue / scheduler
- GUI control plane
- 永続 DB memory
