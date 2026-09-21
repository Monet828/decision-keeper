# Asset Evaluation: T4-human

## 判定: 保留（根拠不足・未観測・人の確認が必要）

自動確認できない Condition（human / document_search）を含むため、完全自律では適用しない（原典§5, EA-08）

終了コード: `20`

## Engineering Context

Asset Layer は状況を構造化して提供するところまでを担う。
どのモデルを使うかはここでは決めない（原典§16）。

| フラグ | 値 |
|---|---|
| `asset_found` | true |
| `reuse_possible` | false |
| `decision_conflict` | false |
| `evidence_gap` | true |
| `human_review_required` | true |

- 自動確認できない Condition を含む
- 観測できていない Condition が 1 件

## Asset DEC-009 v1 — hold

DEC-009 を選択した。キーワードの一致: 遅延を許容、SLA、遅延を認め

### FACTS — Evidence（観測事実）

**EV-0003** (`not_observed`)

- 観測: `{"observed": false, "reason": "verifier.type=human は自動確認できない。人の確認が必要"}`
- 問い合わせ: `{"verifier": "human", "targets": []}`

### INTERPRETATION — ConditionEvaluation（判定）

| Condition | 判定 | 根拠Evidence | 理由 |
|---|---|---|---|
| C1 | **観測できていない** | EV-0003 | 観測できていない。verifier.type=human は自動確認できない。人の確認が必要 |

## Asset DEC-007 v1 — inherit

DEC-007 を選択した。変更パスの一致: src/auth/permissions.py が src/auth/* に一致 / キーワードの一致: キャッシュ、cache、権限、permission

### FACTS — Evidence（観測事実）

**EV-0001** (`grep_result`)

- 観測: `{"files_scanned": 2, "matches": 0}`
- 問い合わせ: `{"patterns": ["invalidate", "revoke", "purge"], "targets": ["src/auth/*", "src/cache/*"]}`

**EV-0002** (`grep_result`)

- 観測: `{"files_scanned": 1, "matches": 1}`
- 問い合わせ: `{"patterns": ["失効", "監査対象", "audit"], "targets": ["docs/audit/*"]}`

| ファイル | 行 | 該当 |
|---|---|---|
| `docs/audit/permission-audit.md` | 3 | `権限の失効は監査対象である。失効操作から反映までの遅延を記録すること。` |

### INTERPRETATION — ConditionEvaluation（判定）

| Condition | 判定 | 根拠Evidence | 理由 |
|---|---|---|---|
| C1 | **支持された** | EV-0001 | 2 ファイルを走査し 0 件一致。探索した結果として存在しないことを確認した |
| C2 | **支持された** | EV-0002 | 1 ファイルを走査し 1 件一致。期待 present と観測が一致した |

## Implementation Asset の再利用可否

再利用可: なし

再利用しない: `IMP-018`

## 注記

- 未承認のため検索対象から除外: DEC-C900 (status=candidate)
- 評価した Asset: DEC-009=hold、DEC-007=inherit → 全体は最も保守的な hold
- 実装資産 IMP-018 は再利用対象にしない。自動確認できない Condition があり、人の確認が必要（EA-08）

## 確認

- Approved Asset の不変性 (EA-03): 確認済み（変更なし）
- 実装資産の適用とテスト実行は今回の範囲外（§18）
