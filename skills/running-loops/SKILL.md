---
name: running-loops
description: Loop engineering for long or multi-session work — tracking execution state, setting step and retry budgets, verifying before claiming done, and leaving a Resume From handoff so the next session can restart from the filesystem rather than from memory. Use for work spanning multiple sessions, for tasks that risk unbounded retry loops, or when stopping while blocked.
---

# Loop Engineering v1

長い作業では、**実行状態・検証・再開可能性**を明示する。頭の中に置かない。

## Loop State

`memory/sessions/` に残す。

```text
current:           現在の実行状態
last_verified_at:  最終検証時刻
step_budget:       このセッションで進める最大ステップ目安
retry_budget:      再試行の最大回数目安
```

**推奨 state**:

```text
goal_defined → context_loaded → plan_selected → execute → verify → checkpoint → done
                                                                              ↘ blocked
```

## Budget の考え方

- **`step_budget`** — 無制限に探索や修正を繰り返さないための上限。
- **`retry_budget`** — 同じ失敗を繰り返す前に停止して再判断するための上限。

厳密な数値最適化は不要。ただし**長い作業では空欄にしない**。

> [!warning] 同じ失敗を3回繰り返したら、やり方が間違っている
> retry_budget を使い切ったら、修正を続けるのではなく**止まって前提を疑う**。
> エラーメッセージを読み直す、別のアプローチを検討する、人間に確認する。

## Verifier の扱い

- 完了とみなす前に、**少なくとも一度は verifier 観点で見直す**。
- 小さな作業でも、**何を確認し、何を未確認のまま残したか**を明示する。
- テストを実行できなかった場合は、未確認点として残す（成功扱いにしない）。
- `./scripts/loop/verify.sh` の `[SKIP]` は成功ではない。

## Resume の扱い

作業を止めるとき、特に `blocked` で終えるときは **`Resume From` を残す**。

```markdown
## Resume From

next_state:  execute
理由:        Supabase の RLS ポリシーが期待通り効かず、原因未特定で停止
必要な文脈:  - 再現手順は memory/sessions/2026-08-30.md の「再現」節
             - 試した3つの仮説と、それぞれの否定根拠は同ファイル
             - src/db/policies.sql:40-58 が該当箇所
未確認:      本番環境で同じ挙動が出るかは未検証（ローカルのみ確認）
```

**次回作業者は、最初に `Resume From` を見てから再開する。**

## 未確定事項の扱い

- open question は頭の中だけに残さず、**session に書く**。
- 小さい未確定事項でも、次の判断に影響するなら
  `Unresolved / Open Questions` に残す。
- 今回解かないが**次回見落とすと危険な論点**は、`memory/current-state.md` や
  `memory/tasks.md` にも昇格する（→ `skills/managing-memory/SKILL.md`）。

## 関連コマンド

- `./scripts/loop/verify.sh` — 実チェック（`[PASS]/[SKIP]/[FAIL]`）
- `./scripts/loop/record-verification.sh` — verify.sh 実行後に結果を session へ記録
- `./scripts/loop/resume.sh` — 再開
