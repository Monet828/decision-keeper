# CLAUDE.md

Claude Codeは、このリポジトリで作業する前に必ず `AGENTS.md` を読むこと。

`AGENTS.md` が、このプロジェクトにおけるAIエージェント共通の作業ルールである。

## 役割

`CLAUDE.md` は補助アダプタであり、ルール本体ではない。
共通ルール、メモリ運用、Goal-Bounded Autonomy は必ず `AGENTS.md` を正本として参照すること。

## Claude Code固有の運用

- Claude Code固有のHookやCommandは、可能な限り `scripts/` 配下の共通スクリプトを呼び出す形にする。
- Claude Codeの内部記憶を正本にしない。現在の状態は `memory/current-state.md`、設計判断は `memory/decisions.md` を参照する。
- `AGENTS.md` と矛盾するローカル判断を優先しない。
- 作業開始時は `./scripts/hooks/pre-task.sh` または `./scripts/setup/bootstrap.sh` を優先して使う。
- 作業終了時や停止時は `./scripts/hooks/post-task.sh` と `./scripts/hooks/save-memory.sh` を優先して使う。
- loop を再開するときは `./scripts/loop/resume.sh` を優先して使う。
- 完了前の見直しには `./scripts/loop/verify.sh`（実チェック）を実行し、`./scripts/loop/record-verification.sh`（結果と所感の記録）を優先して使う。
- 未確定事項は流しやすいので、判断保留の論点は `memory/sessions/` の `Unresolved / Open Questions` に残す。
- 次回に影響する未確定事項は、必要に応じて `memory/current-state.md` または `memory/tasks.md` にも残す。

## この大会プロジェクトの再開入口
最初に `docs/handoff/START-HERE.md` を読み、既に議論した企画を引き継ぐ。セットアップ承認を製品実装・設計の承認と混同しない。
