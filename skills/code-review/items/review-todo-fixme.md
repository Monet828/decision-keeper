# review-todo-fixme — 新規 TODO/FIXME の検出（方針判断要）

## 根拠 (Basis)
変更行に新しく入った TODO/FIXME/XXX/HACK は「未完了の宣言」。放置すると
技術的負債が無言で溜まる。ただし機械的に消すべきでない（意図がある）ため、
**自動修正せず報告し、人間の方針判断に回す**。

## 検査対象 (Target)
変更差分の **追加行のみ**（既存の TODO は対象外。差分の `+` 行を見る）。
**除外**: テストのフィクスチャ、ドキュメント内の説明的言及。

## 規約 (Rule)
新規 TODO/FIXME/XXX/HACK は、課題化（tasks.md / issue）するか、対応してから
マージする。放置コミットしない。

```
❌ // TODO: あとで直す（追跡なし）
✅ // TODO(#123): 認証リトライを指数バックオフに（memory/tasks.md 記載済み）
```

## 検出方法 (Detection)
```sh
# 追加行だけを対象にする（ベース比較の diff から + 行を抽出して grep）
git diff "${base}"...HEAD | grep -nE '^\+.*\b(TODO|FIXME|XXX|HACK)\b'
# 作業ツリー分
git diff | grep -nE '^\+.*\b(TODO|FIXME|XXX|HACK)\b'
# 除外: 既存行（+ が付かない行）/ ドキュメント / テストフィクスチャ
```

## 報告フォーマット (Report)
自動修正せず、**方針判断要** として報告する。
```
file:line — 新規 <TODO/FIXME/XXX/HACK>: "<内容>" — 課題化 or 今回対応を判断（方針判断要）
```
