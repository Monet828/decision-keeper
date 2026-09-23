# 仕様 — Engineering Assets v0.1

## 状態

| 項目 | 内容 |
|---|---|
| 対象 | Engineering Asset のデータモデルと Execution Agent の検索・評価 |
| 版 | 0.1.0 |
| 承認状態 | 要件承認済み（ユーザー提示の要件定義 v0.1） |
| 承認記録 | `docs/approvals/engineering-assets.md` |
| 最終更新 | 2026-09-21 |

原典はユーザーが提示した「Engineering Assets 要件定義 v0.1」。本書はそれを
実装可能な粒度に落とし、既存 decision-keeper との対応と、確認した不整合の裁定を記す。

## 裁定した不整合（原典に食い違いがあった箇所）

| 箇所 | 食い違い | 裁定 |
|---|---|---|
| §0 循環図 / §9 例 / §9本文・§15 | verdict が `Reuse/Adapt/Challenge/Hold` / `challenge` / `inherit/propose_update/hold` の3通り | **`inherit` / `propose_update` / `hold` の3種を正とする** [確定: ユーザー選択]。§0図と§9例は誤記として扱う |
| §16 と現行実装 | 「モデル選択は Asset Layer の責務ではない」。現行 `context.py` はモデル選択まで行っている | **モデル選択を Asset Layer から外す** [確定: §16に従う]。Asset Layer は Engineering Context の構造化まで |
| §18 MVP範囲 と 前回指示 | §18 は「検索・評価」まで。前回指示は「適用・テスト実行・資産候補へ戻す」まで | **§18どおり検索・評価までとする** [確定: ユーザー選択]。適用とテスト実行は次回 |

## 1. 何を作るのか

開発中に生じた実装・技術判断・検証結果を、将来の Execution Agent が安全に再利用できる
**Engineering Asset** として表現し、現在の条件で再評価できるようにする。 [確定: 原典§0]

今回作るのは、そのうち**データモデルと評価経路**である。 [確定: 原典§18]

## 2. 今回作らないもの

原典§19 に加えて、今回の範囲外:
- 実装資産の実際の適用、テスト実行、結果の資産候補への反映 [確定: ユーザー選択]
- OrcaReplay からの抽出（Extractor 本体）。provenance の受け口だけ用意する [確定: 原典§18]
- モデル選択（Asset Layer の責務外。呼び出し側へ移す） [確定: 原典§16]
- UI、自動PR、サンドボックス実行、実アプリ適用 [確定: 前回指示]

## 3. データモデル

### 3.1 共通
```yaml
id: DEC-007 | IMP-018
type: decision | implementation
version: 1
status: candidate | approved | deprecated | superseded   # 原典§11
supersedes: [DEC-007-v1]                                  # 原典§10
provenance:                                               # 原典§13
  - {type: orca_run|pull_request|commit|issue|adr|test_result|benchmark|document|human_input, ref: ...}
related_assets:                                           # 原典§14
  - {id: ..., relationship: implements|implemented_by|supersedes|superseded_by|relates_to}
```

### 3.2 Decision Asset（原典§2.2）
```yaml
question: ...
decision: ...
rationale: {status: known|unknown, text: ...}   # 原典§12: 推測で埋めない
conditions: [Condition]
alternatives: [{option, rejected_because}]
applies_to: {paths: [...], keywords: [...]}     # 検索用。既存から引き継ぐ
```

### 3.3 Condition（原典§4）
```yaml
id: C1
statement: ...
expectation: present | absent
verifier:
  type: grep | file_exists | config_value | dependency_version | test | document_search | human
  targets: [...]
  patterns: [...]
source: ...
status: active | retired
```

`human` および `document_search` は自動確認できない。原典§5により、
これらを含む Decision Asset は Execution Agent が完全自律で適用してはならない。

### 3.4 Implementation Asset（原典§2.1）
```yaml
purpose: ...
implementation: {repository, commit, paths: [...], entrypoint}
compatibility: {runtime, dependencies: [...], requires: [...]}
verification: {tests: [...]}
```
「このコードが存在する」ではなく「この目的を満たす実装が、この条件下で、
この検証を通過した」という主張を表す。 [確定: 原典§2.1]

### 3.5 Evidence（原典§6）— 第一級オブジェクト
```yaml
id: EV-918
type: grep_result | file_list | test_result | config_value | dependency_version | document_hit | human_input
observation: {files_scanned: 24, matches: 0, ...}
query: {pattern: ..., targets: [...]}
source: {repository, commit}
```
Evidence 自身に判断を入れてはならない。 [確定: 原典§6]

### 3.6 ConditionEvaluation（原典§8）
```yaml
condition_id: C2
evidence: [EV-918]
judgment: supported | contradicted | insufficient | not_observed
evaluated_at: ...
evaluator: ...
```
0〜1 の confidence 値は採用しない。 [確定: 原典§8]

### 3.7 AssetEvaluation（原典§9）
```yaml
asset_id: DEC-007
task_id: TASK-311
condition_evaluations: [...]
verdict: inherit | propose_update | hold
evidence: [EV-918]
human_review_required: true | false
```

## 4. 要件

| ID | 要件 | 確認方法 | 状態 |
|---|---|---|---|
| EA-01 | Asset を candidate / approved / deprecated / superseded の4状態で持つ | 各状態のYAMLを読み込み、状態が保持される | [確定] |
| EA-02 | candidate は Execution Agent の通常検索で利用してはならない | candidate のみのディレクトリで検索結果が0件になる | [確定] |
| EA-03 | Approved Asset を書き換えてはならない。変更は新版＋`supersedes` で行う | 実行前後でapproved資産のSHA-256が不変。v2候補が`supersedes`を持つ | [確定] |
| EA-04 | Evidence を第一級オブジェクトとして持ち、判断を含めてはならない | Evidenceのスキーマに judgment 相当のフィールドが無い | [確定] |
| EA-05 | ConditionEvaluation は supported/contradicted/insufficient/not_observed のいずれか | 4種すべてを出せることをテストで確認 | [確定] |
| EA-06 | 「探索して0件」と「探索していない」を区別する | 前者は expectation:absent に対し supported、後者は not_observed | [確定] |
| EA-07 | 確認できない情報を補完してはならない。`unknown`/`needs_review` として保持する | rationale が trace から取れない場合 `status: unknown` になる | [確定] |
| EA-08 | 自動確認不能な Condition（human / document_search）を含む場合、`human_review_required` を立てる | 該当Assetの評価で true になり、verdict が hold になる | [確定] |
| EA-09 | Implementation Asset と Decision Asset を relation で接続する。片方だけの存在も許容する | 双方向の relation をたどれる。Decisionのみ/Implementationのみが読み込める | [確定] |
| EA-10 | すべての Asset は provenance から出典へたどれる | provenance が空の Asset は approved にできない | [確定] |
| EA-11 | Engineering Context を構造化して提供する。モデル選択は行わない | `asset_found`/`reuse_possible`/`decision_conflict`/`evidence_gap`/`human_review_required` を出す。Asset Layer に選択ロジックが無い | [確定] |
| EA-12 | Execution Agent は Task に対し Asset を検索し、Condition を検証して verdict を返す | 3事例で inherit/propose_update/hold が出る | [確定] |
| EA-13 | **差分が無い Task では、`applies_to.paths` を「リポジトリに実在するか」で照合する** | 変更0件の検証専用 run でも、該当 Asset が検索に出る | [確定: 2026-09-23] |
| EA-14 | **active な Condition を持たない Decision は「参照メモ」として扱い、verdict に入れない** | Condition 0 件の Decision だけが該当したとき verdict が出ず、briefing には載る | [確定: 2026-09-23] |

## 5. 既存 decision-keeper との対応

| 新 | 既存 | 扱い |
|---|---|---|
| `question` / `decision` | `problem` / `chosen_decision` | 改名 |
| `conditions[]` | `assumptions[]` | 改名。`verify`→`verifier`、`expect`→`expectation` |
| `contradicted` | `disputed` | 改名 |
| `not_observed` | （insufficient に混在） | 分離 |
| `ConditionEvaluation` | `AssumptionJudgement` | 拡張 |
| `AssetEvaluation` | `ReviewResult` に混在 | 分離 |
| verdict 3種 | 同じ | そのまま |
| 候補の既定除外 | 実装済み | そのまま（EA-02） |
| Observation/Interpretation 分離 | 実装済み | そのまま（原典§7） |
| `selected_model` | `context.py` | **Asset Layer から外す**（EA-11） |

## 6. 判断の分担

- **任せる**: モジュール分割、ファイル配置、レポート整形、合成事例の中身、テストの書き方
- **確認する**: 上記スキーマの変更、verdict 語彙の変更、CLI の引数と終了コード

## EA-13 の背景（2026-09-23 実測）

台帳の実走行3件のうち2件が `no_asset` で終わっていた。原因を追うと、
**`applies_to.paths` による照合が、実質的に一度も働いていなかった**。

`_match()` はパターンを `changed_paths`（差分から取り出した変更ファイル）と突き合わせる。
ところが `start`（着手時）は**作業前に走るので差分が常に空**であり、
`p105-w3-auth-verify-recheck`（検証だけの run）も変更0件だった。
結果、**パス照合の枝は死んでおり、実際にはキーワード照合だけで資産を引いていた**。

これは目的と向きが逆である。Engineering Asset の要点は
「過去の判断の Condition がまだ成り立つか確かめる」ことであり、
**何も変更していない回こそ照合したい**。現状は「コードを変えたときだけ資産が出る」形だった。

**是正**: `changed_paths` が空のときに限り、`applies_to.paths` を
**リポジトリに実在するファイル**と照合する。差分があるときは従来どおり変更パスだけを見る
（差分がある回にまで範囲照合を足すと、広い Asset があらゆる変更に当たってしまう）。

選定理由の文字列で両者を区別する。

- 変更パスで当たった → `変更パスの一致: ...`
- 範囲の実在で当たった → `適用範囲がリポジトリに存在: ...`

⚠ **限界**: 範囲照合は Asset 数に対して線形に緩い。`src/server/*` のような広い
`applies_to.paths` を持つ Asset は、そのリポジトリのあらゆる Task に当たる。
資産が数十件を超えたら、範囲照合には別の絞り込み（Task 種別・鮮度・関連）が要る。
**現在 6 件なので問題にならない**が、増えた時点で再設計する。

## EA-14 の背景（2026-09-23）

### なぜ必要か

Condition（機械が確かめられる形の前提）を書くのは重い。判断そのものは
「Basic 認証にする」で済むが、Condition は「**それが正しくなくなるのはどういうときか**」を
verifier が走る形で書く必要がある。

一方、実際の開発で効いたはずの知識の多くは、Condition を必要としない。
2026-09-22〜23 の実作業で起きた取りこぼし3件を振り返ると、いずれも
**「既に知っていたのに、その瞬間に思い出さなかった」**型だった。

| 取りこぼし | 何が起きたか | 必要だったもの |
|---|---|---|
| `finish` の verify が別リポジトリで走った | 同じ型のバグを Extractor で既に直していたのに、この経路を見落とした | 「このバグは複数経路にある」というメモ |
| Dockerfile の `ENV REEL_PORT` | 同じ PR で、直したばかりの `PORT` の修正を自分で潰した | 「PORT の扱いは今直したところ」というメモ |
| スモークテストの取り違え | 静的マウント側を叩いていて、クエリ経路を通していなかった | 「前にも同じ取り違えをした」というメモ |

**3 件とも機械検証可能な Condition では防げず、ただのメモで防げた。**
必要なのは検証ではなく、適切な瞬間に目の前へ出ること（＝EA-13 で引けるようになった部分）。

### 何が問題だったか

Condition を 0 件にした Decision は、これまで **`hold`（exit 20）** を返していた。
このままメモ的な Decision を足すと、**足すほど全体が止まり、`inherit` が二度と出なくなる**。
（Implementation Asset は既に Condition を持たずに briefing へ載る形になっていた。
 Decision 側だけがこの経路を持っていなかった。）

### 是正

active な Condition を 1 件も持たない Decision は **参照メモ**として扱う。

- **verdict には参加させない**（`reference_decisions` に分ける）
- **briefing には必ず載せる**（問い・判断・理由・`governed_by`）
- 参照メモしか該当しなかった場合、`evaluation` は `None` になる

これにより「Condition を書けるものだけ書く」運用が成立する。
Condition は後から、**1 行で書けて確実に効くものだけ**足せばよい
（例: DEC-005/C3 の `res\.status\(503\)` は 1 行で、実際に `contradicted → supported` の
反転を検出した）。

### 承認の導線（`approve`）

承認は「YAML を開いて `status` を書き換える」手作業だった。候補が 8 件溜まったまま
1 件しか承認されていない原因なので、`approve` サブコマンドを足した。

変えるのは `status` と `approved_by` の 2 行だけで、本文には触らない。
次の場合は承認を拒む。

- `provenance` が無い（EA-10）
- `[要記述]` が残っている（穴あきの資産が検索に出てしまう）
- 承認者名が空

⚠ **未決**: 参照メモしか該当しなかったときの exit code は、現在 `20`（= 該当なしと同じ）。
ワーカーがこれを「止まれ」と解釈すると、メモが付いただけで停止する。
無人実行を始める前に決める必要がある。
