# Current State

## Current Truth
2026-09-21。AI_dev_template fullで生成し大会文書を追加。プロダクト未実装。
企画: 技術判断の前提を現在の証拠と比較して、継承・更新提案・保留を選ぶ開発保守エージェント。
既存2リポジトリの読み取り調査は完了（`memory/understanding-map.md`）。
`docs/specs/mvp-v0.2.md` の §5 要件 R-01〜R-10 は承認済み（`docs/approvals/mvp.md`、コミット 8fbdb7f）。
`docs/specs/mvp-v0.2-design.md` は未承認。

## Active Work
設計承認待ち。承認されれば app/decision_keeper/ の実装に入る。

## Next Actions
1. 設計案（判断資産スキーマ・CLI契約・依存3点）の確認を取る
2. public リポジトリ `decision-keeper` の作成とpush（権限拒否により保留中、下記参照）
3. 合成リポジトリと事例A/B/Cの作成、実装

## Blockers / Risks
- 提出9/22 15:00（資料記載、タイムゾーン未明記）。残り時間が少ない。
- **public リポジトリ作成が未完了**。`gh repo create --public --source=. --push` が
  Claude Code の auto mode 分類器により Data Exfiltration として拒否された。
  回避は行っていない。ユーザーが自分で実行するか、Bash権限ルールの追加が必要。
- `ORCAROUTER_API_KEY` 未設定。ユーザーが後で共有予定。疎通・残高は未確認。
- 提出フォームURLは大会PDFに記載が無く未確認。Discord等で要確認。
- 記事（Qiita/Zenn）未着手。

## Do Not Change
既存folder-lens/ignightを変更しない。未実装を実装済みと書かない。
要件承認を設計承認と扱わない。判断資産ファイルを人間の承認なしに更新しない。
大会PDFとスポンサー資料要約は公開対象に含めない（.gitignore済み）。

## Git / Last Updated
2026-09-21: ブランチ main、初回コミット 8fbdb7f 済み。リモート未設定・未push・未公開。
秘密情報ファイル・大会PDF・実行ログ・スポンサー資料要約のGit除外を確認済み。
