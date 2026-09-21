# Understanding Map
テンプレートはライブGitHubから取得・READMEと生成処理を確認。
既存folder-lens/ignightの最新コードは未調査。START-HERE.mdの参照先から確認する。
大会PDFと会話から仕様候補を整理。実装の存在を文書から推測しない。

## 2026-09-21 folder-lens 読み取り調査（subagent、read-only）
対象: ~/Desktop/folder-lens
Files read (subagent報告による): package.json, README.md, AGENTS.md, CLAUDE.md,
src/db/schema.ts, src/lib/github-decision-import.ts, drizzle/, tests/, docs/dataset/

### Facts
- 技術: Next.js 16.3.0 + React 19.2.8 + TypeScript。DBは drizzle-orm + better-sqlite3 (SQLite)。
  検証に zod、テストに tsx --test。Python関連ファイルは無い。
- 実装状態: 構想段階ではなく実装済み。drizzle/ に 0000〜0015 の16本のマイグレーション、
  tests/ に8本のテスト、.next/ ビルド成果物、data/ に実DBファイルが存在。
- 位置づけ: README上「Akibako の Engineering Intelligence / Decision Infrastructure 本体」。
- 判断資産スキーマ（src/db/schema.ts）の主要テーブル:
  decisionPoints / decisionEpisodes / decisionEpisodeClaims / decisionEpisodeEvidence /
  evidence / decisionPointCases / capabilities / outcomes / archetypes /
  decisionDatasetReleases / verificationRuns
- decisionEpisodes.interpretationJson の実フィールド（原文）:
  problem, context, constraints, alternatives, chosenDecision, rationale,
  codeBeforeSummary, codeAfterSummary, reviewFeedback, outcome
- FACTS/INTERPRETATION分離が実装されている: sourceFactsJson と interpretationJson が別カラム。
  decisionEpisodeClaims.verificationStatus = proposed|supported|disputed|insufficient。
- LICENSE ファイルは存在しない（find で未検出）。

### Interpretation [候補]
- interpretationJson の10フィールドは concept.md の「判断資産の候補項目」に概ね対応する。
  ただし「見直し条件」に直接対応するフィールドは無く、archetypes.exclusionConditions と
  decisionPoints.decisionCriteria に概念が分散している。AI HACK側では明示フィールドが要る。
- decisionEpisodeClaims.verificationStatus の insufficient は、企画の「根拠不足=保留(C)」に
  そのまま対応する語彙。これは再利用価値が高い。
- 技術スタックが全く異なる（TS/SQLite vs Python/JSON-YAML）ため、コードではなく
  フィールド名と概念設計のみを移植するのが妥当。

### Unknowns
- LICENSE不明のため再利用の法的範囲は未確認。所有者（ユーザー本人）の確認が必要。
- memory/current-state.md は存在せず、codex-queue.jsonl のみ。現在の作業状況は未確認。
- 各テーブルが実際にどれだけデータで埋まっているかは未確認（DB内容は見ていない）。

## 2026-09-21 ignight 読み取り調査（subagent、read-only）
対象: ~/Desktop/ignight

### Facts
- 技術: TypeScript strict + Next.js 16 + Node>=22。DBは PostgreSQL (Drizzle, docker-compose)。
  LLMは @anthropic-ai/sdk（Anthropic Claude 第一者APIが既定、Bedrockは予備で未使用）。
  検証は zod、テストは vitest + Playwright。
- 位置づけ(README): TypeScript/Playwright環境のE2EテストとCI失敗を検知・分類し、
  修正案または証拠付きエスカレーションを作成する Engineering Operations システム。
- 実装状態: tests/ 配下50ファイル、.github/workflows あり、migrations あり。作り込まれている。
  ただし本セッションでは npm test を実行していないため動作は未確認。
- 証拠収集の実装（再利用候補）:
  - src/adapters/github/log-extract.ts : GitHub Actionsログから失敗箇所を正規表現で抽出する純関数。
    全文をLLM/DBに渡さない設計。maxChars で上限管理。
  - src/adapters/github/port.ts : GitHubReader interface
    (listRecentFailedRuns, fetchFailureBundle, readFileAtCommit, downloadArtifact)
  - src/domain/policy/test-shape.ts : TypeScript compiler API で test.skip / .only を AST 検出。
  - src/domain/policy/guard.ts : Policy Guard 本体。
  - src/domain/security/mask.ts, src/adapters/github/sanitize.ts : 秘密情報マスキング。
  - src/adapters/ai/prompt.ts : 構造化出力、PROMPT_VERSION でプロンプト版管理。
    systemPrompt() は引数なし = プロンプトキャッシュのprefix固定を意図した設計。
  - 出力は必ず Zod スキーマで検証 (src/domain/triage/schema.ts)。
- 制御構造: tool_use型の自律エージェントループは実装されていない（grepでヒットなし）。
  代わりに決定論的な単方向パイプライン: 生成 → 差分計算 → Policy Guard → 検証 → 人間
  (src/application/propose-fix.ts)。LLM呼び出しは分類1回・修正案生成1回。
- 上限の実装値: DEFAULT_PROPOSE_LIMIT=1, DEFAULT_CHECK_TIMEOUT_MS=300_000,
  DEFAULT_REMEASURE_ATTEMPTS=20、HTTPリトライ maxAttempts=3。
- LICENSE: ファイル無し。README末尾に「ライセンス: 未定。」と明記。
- AGENTS.md: 自律ループを意図的に避け、決定論的検査を中心に置くと明記。

### 本セッションで直接確認した事実
- ignight/memory/current-state.md は「正本は ~/Projects/ignight」と書いているが、
  `~/Projects/ignight` は存在しない（本セッションで ls 確認）。
  ~/Desktop/ignight の最新コミットは f8385c4 (2026-08-30)。
  → ~/Desktop/ignight が現存する唯一の実体。subagentが挙げた「残骸の疑い」は解消。

### Interpretation [候補]
- 「LLMは1回だけ提案し、決定論的なGuardと再現テストで検証し、人間がレビューする」という
  IgNightの制御構造は、AI HACKの審査観点（信頼性・堅牢性、セキュリティ）と相性が良い。
  自律ループを増やすより、この型を踏襲する方が短時間で説明可能な品質に届く。
- log-extract.ts の「全文を渡さず抽出して上限管理」は、コスト観点でそのまま主張材料になる。
- test-shape.ts の「test.skip/.only の検出」は mvp-v0.1 の R-08
  （テスト削除・検査無効化を修復成功にしない）の直接の実装例。

### Unknowns
- LICENSE未定のため、コードそのものの転用は権利面で要確認。設計思想の参照は別途判断。
- READMEは「Sandbox・Draft PR作成は未実装」と書くが src/adapters/sandbox/docker.ts が存在。
  文書とコードに時間差がある。どちらが現状かは未確認。
