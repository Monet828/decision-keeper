# 判断レビュー: DP-001 (v1)

## 判定: 継承（過去の判断は今も有効）

すべての前提が現在も成立している。過去の判断を継承し、衝突する変更を指摘する（R-04）。

終了コード: `0`

## 資産の選定理由 (R-01)

DP-001 を選択した。変更パスの一致: src/auth/permissions.py が src/auth/* に一致 / キーワードの一致: キャッシュ、cache、権限、permission

## FACTS — 収集した証拠 (R-02)

決定論的なコレクタによる観測結果。LLMは関与していない。

### A-1: キャッシュを即時無効化する機構が存在しない

- 資産が期待する状態: `absent`
- 走査したファイル数: 2
- 検出した証拠: **0 件**
- コレクタの記録: 2 ファイルを走査し、パターン /invalidate|revoke|purge/ に一致する行を 0 件検出した。

証拠は **0 件**。走査した結果として0件であり、未調査ではない。

### A-2: 権限の失効は監査対象であり、監査要件が文書化されている

- 資産が期待する状態: `present`
- 走査したファイル数: 1
- 検出した証拠: **1 件**
- コレクタの記録: 1 ファイルを走査し、パターン /失効|監査対象|audit/ に一致する行を 1 件検出した。

| ファイル | 行 | 該当 |
|---|---|---|
| `docs/audit/permission-audit.md` | 3 | `権限の失効は監査対象である。失効操作から反映までの遅延を記録すること。` |

## INTERPRETATION — 前提の判定 (R-03)

| 前提 | 判定 | 理由 |
|---|---|---|
| A-1 | **支持された** | 2ファイルを走査して無効化機構に一致する行が0件検出されており、expect=absentの期待と決定論的な観測が一致したため。 |
| A-2 | **支持された** | docs/audit/permission-audit.mdに権限の失効が監査対象である旨の記述が検出され、expect=presentの期待と観測が一致したため。 |

## 衝突する変更箇所 (R-04)

| ファイル | 行 | 該当 |
|---|---|---|
| `src/auth/permissions.py` | 5 | `from src.cache import store` |
| `src/auth/permissions.py` | 9 | `cached = store.get(f"perm:{user_id}")` |
| `src/auth/permissions.py` | 10 | `if cached is not None:` |
| `src/auth/permissions.py` | 11 | `return cached` |
| `src/auth/permissions.py` | 14 | `perms = set(row["perms"]) if row else set()` |
| `src/auth/permissions.py` | 15 | `store.put(f"perm:{user_id}", perms)` |
| `src/auth/permissions.py` | 16 | `return perms` |

## 実行記録 (R-07)

| 工程 | モデル | 入力トークン | 出力トークン | 推定費用 | 所要秒 | 種別 |
|---|---|---|---|---|---|---|
| judge_assumptions | `glm-5.3-flash` | 1473 | 946 | 未算出 | 21.92 | 実呼び出し |

- 判断資産の不変性 (R-05): 確認済み（変更なし）
- 上限による打ち切り (R-08): なし

## 限界

- 合成データ1リポジトリでの結果であり、本番リポジトリでの有効性は示していない。
- 前提の判定はLLM出力に依存し、誤判定率は測定していない。
- テスト無効化の検出は正規表現によるもので、AST解析ではない。
