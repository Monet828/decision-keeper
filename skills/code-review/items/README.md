# items/ — 規約項目レジストリ

## 仕組み

- **1 ファイル = 1 ルール**。各ファイルは `_TEMPLATE.md` の 5 セクション
  （根拠 / 検査対象 / 規約 / 検出方法 / 報告フォーマット）に従う。
- `SKILL.md`（監査オーケストレーター）が、この dir の `*.md`
  （`_TEMPLATE.md` と本 `README.md` を除く）を全て読み、各項目の
  `grep -nE` を変更差分に適用する。
- 検査は grep ベースで機械的・二値（❌/✅）。重大度は付けない。

## ルールの追加 / 削除

- **追加**: `_TEMPLATE.md` をコピー → `review-<名前>.md` を作成 → 5 セクションを
  埋める（特に「検出方法」はコピペで動く `grep -nE`）→ 下の一覧に追記。
- **削除**: ファイルを消し、一覧から外す。

## スタック固有ルール

ここには **プロジェクトのスタック固有ルール**（TypeScript / Next.js
など）を足してよい。参照バンドルのような 27 項目のスタック規約を、この形式に
落として各プロジェクトに置く運用を想定している（例: reelscore に借用可能）。
スタック非依存の共通項目は下記スターターとして同梱している。

## 一覧（スターター: スタック非依存）

- `review-no-secrets.md` — ハードコードされた秘密情報・API キー・トークン禁止
- `review-no-debug-logging.md` — 本番パスに残ったデバッグ出力禁止
- `review-error-handling.md` — 握りつぶし / 空 catch・except 禁止
- `review-no-hardcoded-config.md` — URL / ホスト / ポート / 絶対ローカルパスの直書き禁止
- `review-todo-fixme.md` — 変更行に新規 TODO/FIXME/XXX/HACK（報告・方針判断要）
- `review-push-governance.md` — push ガバナンスをバイパスするコード / CI の検出
