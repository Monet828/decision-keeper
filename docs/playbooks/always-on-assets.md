# 普段の開発に資産を寄り添わせる（常時運用）

実験用のセットアップではなく、普段の作業の前後に1コマンドずつ挟むだけで回る形。

## 使い方

```bash
cd <このリポジトリ>/app

# 着手時
python3 -m decision_keeper start \
  --task-id <タスクID> \
  --repo <作業対象リポジトリ> \
  --task-file <タスク記述.md> \
  --assets ../assets/engineering \
  --root ../artifacts

# → 資産を検索し、条件を現在のコードで再検証し、
#    ../artifacts/briefings/<タスクID>.md に手渡し資料を出す
#    ここから Experience の記録が始まる

# ここで実際に開発する（人でも AI でも）

# 完了時
python3 -m decision_keeper finish \
  --task-id <タスクID> \
  --repo <作業対象リポジトリ> \
  --verify "npm run typecheck" \
  --verify "npx tsx --test tests/<対象>.test.ts" \
  --assessment matched \
  --note "..." \
  --root ../artifacts

# → 着手時点からの差分・検証結果を記録し、資産候補を抽出し、台帳へ積む

# 実績の確認
python3 -m decision_keeper ledger --root ../artifacts
```

## 何を積んでいるか

A/B の定量比較はここでは行わない（毎回の作業を2倍にしないため）。
積むのは **「機械が出した判断が当たったか外れたか」の実績**。

| 記録するもの | 誰が決めるか |
|---|---|
| 引き当てた資産、verdict、指摘した前提 | 機械（着手時。後から書き換えない） |
| 変更したパス、検証コマンドの終了コード | 機械（完了時） |
| **人の評価（matched / diverged / not_applicable）** | **人** |

`unrecorded` は「人がまだ評価していない」という意味であり、成功でも失敗でもない。

最も価値が高いのは、**機械が `contradicted` / `insufficient` を出し、
それが実際に正しかった**ケース。台帳の「前提の崩れを指摘した回数」がそれにあたる。

## 運用上の注意

- **成否は「落ちなかったか」で判定しない。** `--verify` に指定したコマンドの終了コードで決める。
- 対象リポジトリの全体テストが既に失敗している場合、それを合否に使わない。
  変更前後で失敗数が増えていないかを別途見る。
- **git worktree を使う場合、`node_modules` は複製されない**（gitignore 対象のため）。
  元リポジトリの `node_modules` へシンボリックリンクを張ると `npm install` を繰り返さずに済む。
  実測: これを忘れると検証コマンドが `tsc: command not found` で終了コード 254 になる。
- 着手時の記録は上書きしない。同じタスクIDで `start` を二度打つと拒否される。
