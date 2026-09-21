# AI HACK — 技術判断を継承・更新する開発保守エージェント

Claude Codeへの入口は `docs/handoff/START-HERE.md`。現在はセットアップ済み、プロダクト未実装です。

## 構成
普段の AI_dev_template の full プロファイルを維持し、大会向け文書だけ追加しています。
- `app/`: 実装先。言語・フレームワークは未決定
- `docs/specs/`: 要件候補。設計承認とは分離
- `docs/hackathon/`: 企画・大会ルール・比較デモ
- `docs/submission/`: 記事草稿
- `docs/handoff/`: Claude Codeへの引き継ぎ・セットアップ手順
- `tests/fixtures/`: 今後作る合成デモデータ
- `artifacts/`: 検証証拠・費用測定。生成物は原則Git対象外
- `references/private/`: 大会PDF。ローカル参照用・Git対象外
- `memory/`: 進捗、決定、タスク

OrcaRouterのクレジットはユーザー申告で解放済み。キーは未設定・未検証。課金呼び出しは行っていません。

## 再開
このフォルダをClaude Codeで開き、次を伝えてください。

> docs/handoff/START-HERE.md を読み、既存の空き箱・IgNightの再利用候補を読み取り専用で確認してください。企画を作り直さず、未決のMVP範囲と技術構成だけを具体化し、要件と設計を区別して確認したうえで実装に進んでください。

## 検証
`./scripts/setup/doctor.sh` は構成確認、`./scripts/loop/verify.sh` は設定済みのチェックを実行します。現時点でアプリのテストやビルドは未設定です。
