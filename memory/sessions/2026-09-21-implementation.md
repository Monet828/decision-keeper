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

## 実LLM（OrcaRouter）での検証 — 2026-09-21 追記

APIキーをユーザーから受領し `.env` に格納（600、Git除外）。値はチャット・ログ・コミットに出していない。

### 疎通で分かった事実
- `orcarouter/auto` は `glm-5.3-flash` に振られた（推論型モデル）
- 単純な呼び出しでも completion_tokens の大半が reasoning_tokens に消える
- `response_format: {"type":"json_object"}` は機能する

### 3回の失敗と、その原因（すべてこちら側の不備）
1. **ReadTimeout**: httpx のタイムアウトを60秒固定にしていた。本番プロンプトで超過。
   → `--timeout-sec` 連動（既定180秒）に変更。
   防御は正しく働き、呼び出し失敗を成功扱いせず insufficient → hold になった。
2. **JSON破損**: `max_tokens=4000` では推論トークンで枠を使い切り、出力が途中で切れた
   （A/B とも completion_tokens が 4000/4000 に張り付き）。
   → DEFAULT_MAX_TOKENS を 12000 に引き上げ。
   スキーマ検証が壊れた出力を弾き、insufficient → hold になった。
3. **判定の誤り**: プロンプトの欠陥。下表のとおり2回改訂した。

### プロンプト改訂の経緯
| 版 | 変更 | A | B | C |
|---|---|---|---|---|
| 1.0.0 | 初版「証拠が無いことを supported の根拠にするな」 | ❌ | ❌ | ✅ |
| 1.1.0 | 「走査済み0件」と「未観測」を区別 | ✅ | ✅ | ❌ |
| 1.2.0 | `claimed_in_proposal` の意味と使い方を明記 | ✅ | ✅ | ✅ |

1.0.0 の誤りは、こちらが書いた安全条項が設計意図と矛盾していたこと。
走査して0件だったことは expect=absent に対する積極的な証拠であり、未観測ではない。
1.1.0 の誤りは、ペイロードに渡している `claimed_in_proposal` を
プロンプトで一度も説明していなかったこと。モデルは毎回、書かれた指示に忠実だった。

### モデルの指摘で資産を修正した
実LLMが「docs/audit のファイル存在のみが確認されており、内容が監査要件を記述しているかは
検証されていない」と指摘。正当な批判だったため、A-2 の verify を
file_exists から grep（内容検査）に変更した。

### 最終結果（PROMPT_VERSION 1.2.0）
| 事例 | 判定 | 終了コード | 入力/出力トークン | 所要 |
|---|---|---|---|---|
| A | inherit | 0 | 1473/946 | 22s |
| B | propose_update | 10 | 1712/1162 | 25s |
| C | hold | 20 | 1471/1134 | 27s |

固定応答クライアントの判定と実LLMの判定が3事例とも一致することを確認した。
R-08 は実キーがある状態でも呼び出し0回で停止することを確認した。

### Unresolved / Open Questions（更新）
- **実請求額は未確認**。トークン数は取得できたが単価が不明なため、
  推定費用は捏造せず「未算出」のままにしてある。OrcaRouter管理画面での確認が必要。
- 実呼び出しは計16回。判定が安定するかの反復試行（同一入力の複数回実行）は未実施。
  temperature=0 だが、1.1.0 時点で同一証拠に対し事例間で判定が揺れた記録がある
  （A/Cでは supported、Bでは insufficient）。再現性は未測定。
- R-09 は構造的隔離を確認しただけで、実LLMに対する注入耐性は未検証。
- `ast_test_shape` は正規表現であり、AST解析ではない。
