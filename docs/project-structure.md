# Project Structure

このドキュメントは、`AI_dev_template` における推奨ディレクトリ構成を定義する。

## 目的

- 正式仕様と再利用資産を分離する
- 実装本体とテストを明確に分ける
- Claude / Codex どちらでも迷いにくい入口を作る
- `app/` 中心の Web アプリ構成を標準化する

## 主要ディレクトリ

### `app/`

デプロイ対象のアプリ本体を置く。  
Web アプリや BFF/API サービスの第一候補。

主な対象:

- UI
- route handlers / API endpoints
- app 固有の data access
- app 固有の type definitions

### `src/`

`app/` から切り出した共通ライブラリや、複数アプリで共有するコードを置く。

主な対象:

- domain logic
- shared data access
- SDK
- utility modules
- type definitions

### `tests/`

`app/` や `src/` を検証するコードを置く。

主な対象:

- unit tests
- integration tests
- e2e tests
- fixtures

推奨:

- 可能な限り `app/` や `src/` と対応が分かる構成にする
- テストだけが仕様の正本にならないようにする

### `docs/`

確定した仕様、方針、ADR、運用知識を置く。

主な対象:

- architecture
- setup
- API contracts
- ADR
- operational rules

### `assets/`

仕様そのものではない再利用資産を置く。

主な対象:

- design assets
- reusable reference artifacts
- opt-in pack が導入する補助資産

### `memory/`

AIエージェントと開発者の共有作業記憶を置く。

### `skills/`

再利用可能な AI skill を置く。  
調査、設計、プロトタイプ化、特定ドメイン作業などをモジュール化するための置き場。

主な対象:

- `SKILL.md`
- `references/`
- `assets/`
- skill ごとのテンプレや補助資料

### `scripts/`

bootstrap、doctor、hooks、loop 補助を置く。

## 判断基準

- 長期的に参照される仕様や設計判断は `docs/`
- デプロイ対象の Web アプリは `app/`
- 共有ロジックは `src/`
- 本体の検証は `tests/`
- 再利用資産は `assets/`
- 再利用可能な能力は `skills/`
- セッション記録や短期記憶は `memory/`

## Pack 方針

このプロジェクトは、`AI_dev_template` の本体に、生成時に選択した pack（機能拡張）をマージして作られている。

- 適用された pack とそのバージョンは、プロジェクト直下の `.ai-dev-template.yml` に記録されている。
- pack は生成時に一度だけマージされるものであり、このプロジェクト自身には `packs/` ディレクトリや `scaffold.sh`/`new-project.sh` は含まれない（これらはテンプレート生成元リポジトリ側のツールで、生成後のプロジェクト内には存在しない）。
- 生成後に別の pack を追加したい場合は、テンプレート生成元リポジトリ（`AI_dev_template`）側で改めて `new-project.sh`/`scaffold.sh` を実行するか、必要なファイルを手動でマージすること。

## 大会向け追加
`docs/hackathon/` は企画・大会条件、`docs/submission/` は記事草稿、`docs/handoff/` は引き継ぎ。`tests/fixtures/` は合成事例、`artifacts/` はローカル検証証拠、`references/private/` は公開しない参照資料。docs内でもdraft/候補は承認済み正本ではない。
