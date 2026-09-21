# Engineering Assets v0.1 — Execution Agent の評価結果

要件定義 v0.1 §18 の範囲（データモデルと検索・評価）まで。
実装資産の実際の適用とテスト実行は範囲外。

## 4タスクの結果

| タスク | 状況 | verdict | 終了コード | 人の確認 | 実装資産の再利用 |
|---|---|---|---|---|---|
| [T1](T1-inherit.md) | 無効化機構が無い | inherit | 0 | 不要 | **IMP-018 可** |
| [T2](T2-conflict.md) | 無効化機構があり検証テストもある | propose_update | 10 | 不要 | 不可 |
| [T3](T3-unsupported.md) | タスク説明が「実装済み」と主張するがコードに無い | hold | 20 | 不要 | 不可 |
| [T4](T4-human.md) | 顧客SLAという自動確認できない Condition に当たる | hold | 20 | **必要** | 不可 |

## 要点

**T4 が原典§5 / EA-08 の実演。** `verifier.type: human` を含む DEC-009 に当たったため、
`human_review_required` が立ち、実装資産 IMP-018 を**再利用可にしない**。
DEC-007 単体では inherit だが、人の確認が必要な Condition が別の Asset にあるため、
全体としては自律適用しない。

**該当する Asset はすべて評価する。** T4 では DEC-007（inherit）と DEC-009（hold）の
両方を評価し、最も保守的な hold を全体の verdict にしている。
1件だけ見ると、広い Asset が他を覆い隠す。

**「探索して0件」と「探索していない」を区別する（原典§7, EA-06）。**
T1 の C1 は「2ファイルを走査し0件」で `supported`（expectation: absent に対する積極的証拠）。
対象が存在しない場合は `not_observed` になり、`supported` にはならない。

## Engineering Context（原典§16）

Asset Layer は状況を構造化して提供するところまでで、**モデル選択は行わない**。
`asset_found` / `reuse_possible` / `decision_conflict` / `evidence_gap` /
`human_review_required` を出し、HTTPヘッダーにも落とせる。

## 限界

- 合成事例4件、Asset 4件での結果
- 実装資産の適用とテスト実行は未実装（§18の範囲外）
- OrcaReplay からの抽出は未実装。provenance の受け口のみ用意
