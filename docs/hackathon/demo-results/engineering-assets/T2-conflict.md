# Asset Evaluation: T2-conflict

## 判定: 更新提案（Conditionが変化している）

Condition の前提が現在の観測と食い違う（C1）。判断の見直しを提案する。Approved Asset は書き換えない（EA-03）

終了コード: `10`

## Engineering Context

Asset Layer は状況を構造化して提供するところまでを担う。
どのモデルを使うかはここでは決めない（原典§16）。

| フラグ | 値 |
|---|---|
| `asset_found` | true |
| `reuse_possible` | false |
| `decision_conflict` | true |
| `evidence_gap` | false |
| `human_review_required` | false |

- 前提と観測が食い違う Condition が 1 件

## Asset DEC-007 v1 — propose_update

DEC-007 を選択した。変更パスの一致: src/auth/permissions.py が src/auth/* に一致 / キーワードの一致: cache、権限、permission

### FACTS — Evidence（観測事実）

**EV-0001** (`grep_result`)

- 観測: `{"files_scanned": 3, "matches": 5}`
- 問い合わせ: `{"patterns": ["invalidate", "revoke", "purge"], "targets": ["src/auth/*", "src/cache/*"]}`

| ファイル | 行 | 該当 |
|---|---|---|
| `src/cache/invalidate.py` | 1 | `"""キャッシュの即時無効化。権限変更イベントを購読して purge する。"""` |
| `src/cache/invalidate.py` | 6 | `def invalidate(key: str) -> None:` |
| `src/cache/invalidate.py` | 10 | `def revoke_user(user_id: str) -> None:` |
| `src/cache/invalidate.py` | 11 | `"""権限変更時に該当ユーザーのエントリを即座に purge する。"""` |
| `src/cache/invalidate.py` | 13 | `invalidate(key)` |

**EV-0002** (`grep_result`)

- 観測: `{"files_scanned": 1, "matches": 1}`
- 問い合わせ: `{"patterns": ["失効", "監査対象", "audit"], "targets": ["docs/audit/*"]}`

| ファイル | 行 | 該当 |
|---|---|---|
| `docs/audit/permission-audit.md` | 3 | `権限の失効は監査対象である。失効操作から反映までの遅延を記録すること。` |

### INTERPRETATION — ConditionEvaluation（判定）

| Condition | 判定 | 根拠Evidence | 理由 |
|---|---|---|---|
| C1 | **食い違った** | EV-0001 | 3 ファイルを走査し 5 件一致。期待 absent と観測が食い違う |
| C2 | **支持された** | EV-0002 | 1 ファイルを走査し 1 件一致。期待 present と観測が一致した |

## Implementation Asset の再利用可否

再利用可: なし

再利用しない: `IMP-018`

## 注記

- 未承認のため検索対象から除外: DEC-C900 (status=candidate)
- 実装資産 IMP-018 は再利用対象にしない。判断ゲート: DEC-007=propose_update

## 確認

- Approved Asset の不変性 (EA-03): 確認済み（変更なし）
- 実装資産の適用とテスト実行は今回の範囲外（§18）
