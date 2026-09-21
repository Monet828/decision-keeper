# OrcaReplay 調査結果 — 2026-09-21

実装は今回行わない。次回の入力として使えるかの判断材料として記録する。
調査は読み取りのみ。記録の取得も送信も行っていない。

## 一次情報
- GitHub: https://github.com/Continuum-AI-Corp/OrcaReplay （Apache-2.0）
- 仕様: `spec/orca-trace-v0.md`（Status: Draft、schema 0.1.0、CC BY 4.0）
- JSON Schema: `packages/schema/schema/event.schema.json`（仕様より優先と明記）
- npm: `orcareplay@0.4.0`（Node 20+、bin は `orca`）
- 読み取り専用 Python SDK: `python/orca_trace`（標準ライブラリのみ、py.typed）

OrcaRouter 公式 docs サイトには OrcaReplay の記載が無い。文書はリポジトリ内 `docs/` のみ。

## 記録の形式
保存先は `.orca/runs/<run_id>/`。`manifest.json` / `events.jsonl` / `blobs/` / `fs/` / `redactions.json`。
`events.jsonl` は1行1イベントの追記専用・全順序。
エンベロープ必須: `seq`, `ts`, `mono_us`, `turn`, `type`, `actor`。任意に `causes`（因果DAG）, `attrs`, `payload`。
4096バイト超の payload は content-addressed blob に退避される。

イベント型は27種。判断抽出に使えるもの:
| 型 | 中身（同梱サンプルで実測） |
|---|---|
| `shell.exec` | `{"argv": ["npm","test","--","auth"], "cwd": "/home/dev/api"}` |
| `shell.result` | `{"exit_code": 1, "duration_ms": 8412, "stdout_bytes": 206}` |
| `fs.change` | `{"path": "src/auth.ts", "status": "modified", "insertions": 18, "deletions": 4}` |
| `fs.snapshot` | `{"tree": "<sha>", "files": 214}` |
| `model.request` / `model.response` | モデルが何を見て何を返したか |
| `session.snapshot` | ハーネスのトランスクリプト（ユーザが何を頼んだか） |

`checkpoint` は記録されず、`derive_checkpoints()` で導出される。記録側に仕込みは不要。

## 取得方法
`npm i -g orcareplay` → `orca doctor` → `orca record claude`。
Claude Code 専用アダプタあり（`packages/adapters/src/claude-code.ts`）。
`ANTHROPIC_BASE_URL` を向ける proxy 方式で、エージェント本体は無改造。
完全ローカルで動く。`orca push` でゲートウェイに上げられるが任意。

## 同梱サンプル
`examples/traces/run_9f2c14a03b71`（31イベント、adapter=claude-code）。
自分で記録を取らなくても抽出器を作って試せる。本セッションで中身を実測済み。

## この構想にとっての意味
「人間が判断を書かなくても、実行履歴から判断候補が溜まる」経路の入力になりうる。
比較実験で限界に挙げた「判断資産を人間が書くコストを計上していない」が、
この経路が成立すれば問題でなくなる。
「テストが赤 → この差分 → 緑」は `causes` + `shell.result.exit_code` + `fs.change` で機械的に組める。

## 懸念
- **「なぜそうしたか」は記録されない。** 起きたことだけ。理由はモデル出力の自然言語に埋まっており、
  抽出は結局 LLM による事後解析になる。
- `attrs` は型ごとにスキーマ化されていない自由形式。細目は実装依存。仕様は Draft。
  パーサは未知 `type` をスキップする前提で書くこと（仕様が MUST で要求）。
- README 自身が「トレースは shell history + heap dump 相当のセンシティブ物」と明記。
  redaction は best-effort。蓄積基盤に流すなら扱いを先に決める必要がある。
- 初版 npm 公開が 2026-09-01。仕様 Draft。疎結合に（JSONL を読む層だけに依存し、
  `orca` CLI の出力フォーマットには依存しない）作るのが安全。

## 未確認
- GitHub Releases は未作成（配布は npm のみ）
- push 先ゲートウェイの利用条件
- 「テスト結果」専用のイベント型は無い（`shell.result` の exit code のみ）
