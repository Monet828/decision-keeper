# decision-keeper

過去の技術判断が置いた**前提**が現在も成立しているかを、現在のコードから証拠を集めて判定し、
**継承 / 更新提案 / 保留** に振り分ける CLI。

CIは「テストが通るか」しか見ない。チームが「この理由で、この前提のもとでこう決めた」と
判断したことはコードにもテストにも残らず、結果として **CIが緑のまま、守っていた設計判断が壊れる**。

## 使い方

```bash
pip install -e '.[dev]'
cd app
python -m decision_keeper review \
  --assets ../tests/fixtures/assets \
  --change ../tests/fixtures/cases/B \
  --repo   ../tests/fixtures/cases/B/repo \
  --out    ../artifacts/reports/B.md
```

終了コード: `0` 継承 / `10` 更新提案 / `20` 保留 / `2` 入力エラー / `3` 資産が変更された

APIキー (`ORCAROUTER_API_KEY`) が未設定のときは固定応答クライアントで動く。
その実行はレポート上で「固定応答(stub)」と明示され、判定品質の証拠にはならない。

## 判断資産

1判断 = 1 YAMLファイル。`tests/fixtures/assets/DP-001.yaml` を参照。
語彙は folder-lens の `decisionEpisodes` スキーマを踏襲し、
`assumptions`（前提とその検証方法）と `review_triggers`（見直し条件）を追加している。

```yaml
assumptions:
  - id: A-1
    statement: キャッシュを即時無効化する機構が存在しない
    verify:
      method: grep          # grep | file_exists | ast_test_shape | run_tests
      pattern: 'invalidate|revoke|purge'
      paths: ['src/auth/*', 'src/cache/*']
      expect: absent
```

## 設計

自律ループを持たない。単方向の決定論的パイプラインで、LLM呼び出しは1回だけ。

```
資産選択(決定論) → 証拠収集(決定論) → 前提判定(LLM 1回) → 総合判定(決定論) → レポート
```

**証拠収集にLLMは関与しない。** LLMが担うのは「集まった証拠が前提を支持するか」の判定のみ。
総合判定もLLMに委ねず、下表の規則で決める。

| 前提の状態 | 判定 | 終了コード |
|---|---|---|
| 1つ以上 `insufficient` | 保留 | 20 |
| すべて `supported` | 継承・衝突指摘 | 0 |
| 1つ以上 `disputed`、`insufficient` なし | 更新提案 | 10 |

`insufficient` を最優先で見る。根拠不足を肯定にも否定にも倒さない。

## デモ（同一判断・同一変更、証拠だけが違う）

| 事例 | 状況 | 判定 |
|---|---|---|
| A | 無効化機構が無い | 継承。衝突する変更箇所を指摘 |
| B | 無効化機構があり検証テストもある | 更新提案。**資産は書き換えない** |
| C | 提案文が「実装済み」と主張するがコードに無い | 保留。追加確認項目を提示 |

## 安全機構

| 要件 | 実装 |
|---|---|
| R-05 | 資産を読み込み時にSHA-256記録、終了時に再計算して差異を検出 |
| R-08 | `--max-llm-calls`(既定1) `--max-tokens` `--timeout-sec`(既定300) |
| R-09 | 差分・提案文は `<untrusted_data>` で囲み、観測結果は `<observations>` に分離 |
| R-10 | `skip`/`only`/テスト削除/アサーション削除を検出したら継承判定を出さない |

## 限界

- 合成データ1リポジトリでの結果であり、本番リポジトリでの有効性は示していない
- 前提の判定はLLM出力に依存し、誤判定率は測定していない
- テスト無効化の検出は正規表現によるもので、AST解析ではない
- R-09 の検証は構造的隔離を確認したもので、LLMの堅牢性を示すものではない

## テスト

```bash
pytest          # 要件 R-01〜R-10 の適合検査 16件
./scripts/loop/verify.sh
```
