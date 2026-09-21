---
name: recording-decisions
description: How to make and record an engineering design decision so it stays reusable, covering the required elements (problem, constraints, alternatives, chosen option, rationale, rejected options, future revision conditions) and when a decision graduates from memory/decisions.md to docs/adr/. Use when making an architectural or design choice, when writing to memory/decisions.md, or when promoting a decision to a formal ADR.
---

# 設計判断の記録

## 設計時に明示する要素

設計を行う場合、以下を**すべて**明示する。欠けた項目は「まだ決まっていない」ことを意味する。

- 解こうとしている問題
- 目的
- 制約
- **代替案**（最低2つ。1つしかないものは判断ではなく既定路線）
- 採用案
- 採用理由
- **却下した案**（と、なぜ却下したか）
- 将来の変更余地
- 影響を受けるファイル

## どこに書くか

```text
設計判断が発生
    │
    ├── 今回限り・一時的        → 記録しない（memory/sessions/ に留める）
    ├── 次回以降も参照される    → memory/decisions.md
    └── 長期的に有効な正式方針  → docs/adr/ へ昇格
```

`memory/decisions.md` に含めるもの: 日付 / 決定内容 / 理由 / 却下した案 / 影響範囲 /
将来の見直し条件。

## 却下した案を必ず書く理由

却下した案が残っていないと、半年後に**同じ案が再提案され、同じ議論を最初からやり直す**。
「なぜそれを選ばなかったか」は、選んだ理由と同じかそれ以上に再利用価値がある。

却下理由は具体的に書く:

- ✗ 「複雑すぎるため却下」
- ✓ 「新しい依存を1つ増やすが、現時点で単一インスタンス構成のため、その依存が
  解決する問題（インスタンス間の状態共有）が発生しない」

## 決まっていないことを、決まったこととして書かない

- 検証していない性能・互換性の主張は、**検証していないと明記**する。
- 「著者/ドキュメントがそう主張している」と「自分で確認した」を区別する。
- 未確定の論点は `Unresolved` として残し、決定として書かない。

## 将来の見直し条件

判断は前提に依存する。**前提が崩れたら見直す**ことを明示的に書く。

```markdown
将来の見直し条件:
- 複数インスタンス構成に移行したとき（現在の選択の前提が消える）
- 依存ライブラリが v3 に上がったとき（現在の回避策が不要になる可能性）
```

これが無いと、前提が変わっても誰も気づかず、古い判断が惰性で残る。

## 関連

- 書き込み先の使い分け全般 → `skills/managing-memory/SKILL.md`
- 事実と解釈を混ぜない原則 → `AGENTS.md` §3
