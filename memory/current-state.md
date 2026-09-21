# Current State

## Current Truth
2026-09-21。AI_dev_template fullで生成し大会文書を追加。プロダクト未実装。
企画: 技術判断の前提を現在の証拠と比較して、継承・更新提案・保留を選ぶ開発保守エージェント。
既存2リポジトリの読み取り調査は完了（`memory/understanding-map.md`）。
`docs/specs/mvp-v0.2.md` の §5 要件 R-01〜R-10 は承認済み（`docs/approvals/mvp.md`、コミット 8fbdb7f）。
`docs/specs/mvp-v0.2-design.md` は未承認。

## Active Work
MVP実装済み。実LLM（OrcaRouter）で3事例A/B/Cが設計どおり分岐することを確認した。
PR #1 https://github.com/Monet828/decision-keeper/pull/1 をレビュー待ちで開いている。

## Next Actions
1. PR #1 に実LLMの結果を反映し、ユーザーのレビュー・マージを待つ
2. 記事（ユーザーが並行執筆中）との合流
3. 実請求額の確認と、提出フォームからの提出

## Blockers / Risks
- 提出9/22 15:00（資料記載、タイムゾーン未明記）。残り時間が少ない。
- **実請求額が未確認**。トークン数は取得済みだが単価不明のため推定費用は未算出。
- 判定の再現性（同一入力の反復実行）は未測定。実呼び出しは計16回。
- 記事（Qiita/Zenn）はユーザーが並行執筆中。実装側の素材は artifacts/reports/ にある。
- PR #1 は未マージ。マージは人間の担当（AGENTS.md §9）。

## Do Not Change
既存folder-lens/ignightを変更しない。未実装を実装済みと書かない。
要件承認を設計承認と扱わない。判断資産ファイルを人間の承認なしに更新しない。
大会PDFとスポンサー資料要約は公開対象に含めない（.gitignore済み）。

## Git / Last Updated
2026-09-21: public リポジトリ https://github.com/Monet828/decision-keeper 作成済み。
ブランチ feat/decision-keeper-mvp から PR #1 を開いている。main へは直接積んでいない。
秘密情報ファイル・大会PDF・実行ログ・スポンサー資料要約のGit除外を確認済み。
