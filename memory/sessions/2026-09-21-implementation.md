# 2026-09-21 実装セッション

## Current subproblem
P3: A/B/Cの適用判断を比較できるMVPを、承認範囲で実装する。

## やったこと
- `docs/specs/mvp-v0.2.md` R-01〜R-10 の承認、`mvp-v0.2-design.md` の承認を記録
- `app/decision_keeper/` を実装（models / assets / limits / collect / diff_guard /
  select / llm / judge / verdict / report / __main__）
- `tests/fixtures/` に判断資産 DP-001 と合成事例 A/B/C を作成
- `tests/test_requirements.py` に要件適合検査16件
- public リポジトリ https://github.com/Monet828/decision-keeper を作成

## 検証結果（実測）
`./scripts/loop/verify.sh` → ran: 4, failed: 0（shell syntax / shellcheck / pytest / ruff）
`pytest` → 16 passed

3事例の実行（固定応答クライアント）:
| 事例 | 判定 | 終了コード |
|---|---|---|
| A 無効化機構なし | inherit | 0 |
| B 無効化機構あり＋検証テスト | propose_update | 10 |
| C 提案文の主張のみ | hold | 20 |

安全機構の実測:
- R-05: 実行前後で資産のSHA-256が一致。改竄は verify_unchanged が検出
- R-08: `--max-llm-calls 0` で呼び出し0回、打ち切りを記録、判定は hold
- R-09: 注入文は `<untrusted_data>` の内側、観測結果は外側。判定は注入なしと同一
- R-10: 前提が全て supported でも、skip/アサーション削除を検出して hold に落とす

## Unresolved / Open Questions
- **判定品質は未検証**。固定応答クライアントは決定論的な expectation_met を写しているだけで、
  LLMの判断力を再現していない。実呼び出しでの誤判定率は測っていない。
  実キーが入った時点で3事例を再実行し、判定が一致するか確認する必要がある。
- R-09 は構造的隔離を確認しただけで、LLMが実際に注入に耐えるかは未検証。
- `ast_test_shape` コレクタは正規表現であり、設計案に書いたAST解析ではない。
- OrcaRouterの疎通・残高・モデル名・1回あたり費用はすべて未確認。
- 費用実測（R-07）は実呼び出しが無いため未取得。推定値は捏造せず未算出のままにしてある。
