---
name: session-bootstrap
description: Procedure for starting, scoping, and closing a work session, including which files to read first, how to declare Goal/Scope/Out of Scope/Stop Conditions for goal-bounded autonomy, and how to structure a decision when stuck. Use at the start of any non-trivial task, when resuming previous work, when scoping how far to proceed without asking, or when unsure how to present options to the human.
---

# セッションの開始・範囲設定・終了

## 1. 開始時に読むもの

### 必須

1. `AGENTS.md`
2. `memory/current-state.md`
3. 関連する `docs/`
4. 関連する `src/` の既存実装

### 必要に応じて

5. `memory/decisions.md`
6. `memory/tasks.md`
7. 関連する `memory/sessions/`

## 2. 開始時に整理するもの

読んだうえで、着手前に以下を簡潔に整理する。

- 今回の目的
- 変更対象
- 影響範囲
- 想定リスク
- 確認すべきテスト
- 自律的に進めてよい範囲
- 止まるべき境界条件

## 3. Goal-Bounded Autonomy

合意された目的と範囲の中では、**細かい確認を挟まずに自律的に進めてよい**。

- 目的・対象ファイル・期待成果・制約が十分に合意されているなら、その範囲では止まらない。
- 些細な実装判断、調査順序、軽微な補助修正、検証の段取りは、都度確認を取らずに前進する。
- 途中で得た新情報により最短経路が変わっても、合意済みゴールに資するなら自律的に調整してよい。

### 開始時に明確にする4項目

`memory/sessions/` に残す。

```text
Goal:            今回達成する成果物や状態
Scope:           触ってよいファイル・機能・論点
Out of Scope:    今回は触らない範囲
Stop Conditions: 人間確認が必要になる境界条件
```

### 止まるべき境界条件

`AGENTS.md` §8 が正本。要約すると、目的が曖昧なとき / 範囲を超えるとき /
新しい仕様・アーキテクチャ判断が要るとき / 破壊的・不可逆操作 /
本番・認証・課金・権限・秘密情報 / 安全に完了とみなせないとき。

## 4. 判断に迷った場合

以下の形式で整理して人間に渡す。

1. 現在わかっている事実
2. 不明点
3. 考えられる選択肢
4. 各選択肢のメリット・デメリット
5. 推奨案
6. 人間に確認すべき点

> [!warning] リサーチ段階では推奨案を急がない
> まず一次情報と事実を整理する。解釈・推奨は事実の後段に置く（`AGENTS.md` §3）。

## 5. 終了時に確認するもの

- 何を変更したか
- どのファイルを変更したか
- テスト・Lint・ビルド確認が必要か
- 新しい設計判断が発生したか（→ `skills/recording-decisions/SKILL.md`）
- 次回作業者に引き継ぐべきことがあるか
- 境界条件に到達したか

必要があれば `memory/current-state.md` / `memory/decisions.md` / `memory/tasks.md` /
`docs/` を更新する（→ `skills/managing-memory/SKILL.md`）。

**作業ログを無制限に増やさない。** 不要になった一時情報は整理する。

## 6. 終了時に分けて残すもの

- **達成内容**（検証済みのもの）
- **未解決点**（Unresolved / Open Questions）

途中で止まる場合、特に `blocked` で終える場合は `Resume From` を残す
（→ `skills/running-loops/SKILL.md`）。
