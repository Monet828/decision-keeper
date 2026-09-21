# 承認記録 — Engineering Assets v0.1

## 2026-09-21 / ユーザー提示の要件定義 v0.1 / 全体

**対象**: ユーザーがチャットで提示した「Engineering Assets 要件定義 v0.1」全文。
`docs/specs/engineering-assets-v0.1.md` はそれを実装粒度に落としたもの。

**ユーザー発言**: 要件定義 v0.1 の全文提示（§0〜§20）。

**あわせて選択式確認で確定したこと**:
- §18 の MVP 範囲は「検索・評価」まで。実際の適用・テスト実行・資産候補への反映は次回。
- verdict の語彙は `inherit` / `propose_update` / `hold` の3種を正とする。
  §0 の循環図（Reuse/Adapt/Challenge/Hold）と §9 の例（challenge）は誤記として扱う。

**こちらから指摘し、原典に従って修正するもの**:
- §16「どのモデルを選択するかは Asset Layer の責務ではない」に対し、
  現行 `context.py` はモデル選択（`selected_model` / `select_model()`）まで行っている。
  Asset Layer から分離する。

**未承認のまま残るもの**: Implementation Asset の詳細スキーマ、CLI の引数と終了コード
（`docs/specs/engineering-assets-v0.1.md` §6 の「確認する」側）。
