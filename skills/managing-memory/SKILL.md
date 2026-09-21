---
name: managing-memory
description: Rules for writing to memory/current-state.md, memory/decisions.md, memory/tasks.md, and memory/sessions/, plus the promotion ladder that decides when information moves up to docs/ or docs/adr/. Use when updating any file under memory/, when deciding where a piece of information belongs, or when judging whether something should be promoted to docs/ or discarded.
---

# memory/ の更新と昇格

`memory/` は**AIエージェント間の文脈共有**のために使う。`docs/` は正式仕様（正本）。
矛盾したら `docs/` を優先する。

## どこに書くか（判断の起点）

| 情報の性質 | 置き場所 |
|---|---|
| 現在の作業状況・短期的な前提・失うと困る文脈 | `memory/current-state.md` |
| 実装や運用に影響し、次回以降も再参照される判断 | `memory/decisions.md` |
| 未完了タスク | `memory/tasks.md` |
| その日の作業ログ | `memory/sessions/` |
| 長期的に有効な仕様・正式な設計方針・運用ルール | `docs/` / `docs/adr/` |
| 一時的な推測・未検証の仮説・無効になった試行錯誤 | **どこにも残さない** |

判断に迷ったら: **「次の作業者が `memory/` を見なくても済むべき内容か？」** が昇格の基準。
Yes なら `docs/`。No なら `memory/`。

## memory/current-state.md

現在の作業状況を管理する。

**含めるもの**: Current Truth / Active Work / Next Actions / Blockers / Risks /
Do Not Change / Last Updated

**更新する条件**:

- 作業対象や優先順位が変わったとき
- 現在の真実が変わったとき
- ブロッカーや注意点が生じたとき
- 次回作業者が読まないと危険な情報が生じたとき

## memory/decisions.md

設計判断を記録する。書式と判断の要素は
`skills/recording-decisions/SKILL.md` を参照。

**含めるもの**: 日付 / 決定内容 / 理由 / 却下した案 / 影響範囲 / 将来の見直し条件

**更新する条件**:

- 実装や運用に影響する判断が発生したとき
- 次回以降も参照されると見込まれるとき
- 人間に承認された判断を残す必要があるとき

## memory/tasks.md

**含めるもの**: 優先度 / タスク内容 / 状態 / 関連ファイル / 備考

## memory/sessions/

日ごとの作業ログ。長期的に有効な情報は `current-state.md`、`decisions.md`、
または `docs/` へ**昇格させる**（セッションログに置いたままにしない）。

**含めるとよいもの**: Goal / Scope / Out of Scope / Stop Conditions / Loop State /
Unresolved / Open Questions / Resume From

## 昇格のルール

```text
memory/sessions/  ──長期的に有効なら──>  current-state.md / decisions.md
                                              │
                                    正式仕様になったら
                                              ↓
                                        docs/ · docs/adr/
```

**`docs/` / `docs/adr/` へ昇格するもの**:

- 長期的に有効な仕様
- 正式な設計方針
- 運用ルール
- チームの正本として扱うべき知識
- 将来の作業者が `memory/` を見なくても参照できるべき内容

**昇格しないもの**:

- 一時的な推測
- 未検証の仮説
- セッション中だけ有効なメモ
- すでに無効になった試行錯誤の履歴

## 守ること

- **作業ログを無制限に増やさない**。不要になった一時情報は整理する。
- 一時的な推測を正式仕様として記録しない（`AGENTS.md` 禁止事項）。
- 未検証の仮説を `docs/` に置かない。仮説は仮説として `memory/` に置く。
