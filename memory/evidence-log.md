# Evidence Log
2026-09-21: ユーザー会話により空き箱＋IgNight構想、文章化、独創性の改善、Claude Codeへの移行、指定フォルダ、OrcaRouterクレジット解放を確認。
大会資料: references/private/。ページ対応はdocs/hackathon/event-requirements.md。
前回記事（構成の参考、今回の実装証拠ではない）:
https://qiita.com/jksoft/items/65f7824679ddf171a93d
https://zenn.dev/m_go/articles/794869d594e333

## 2026-09-21 判断資産あり/なしの比較（第1回、交絡あり）

- source type: 自分で実行した測定
- source: `artifacts/reports/comparison.json`（コミット前、実行は 2026-09-21）
- date: 2026-09-21
- 条件: 事例A/B/C、OrcaRouter、資産あり側は難度でモデル切替、資産なし側は claude-sonnet-5 固定。
  各アーム1呼び出し。temperature=0。

### fact（観測値）
| 事例 | 資産あり | 資産なし |
|---|---|---|
| A | inherit / 1848tok | concern / 1823tok |
| B | propose_update / 3312tok | concern / 1517tok |
| C | hold / 3189tok | concern / 1781tok |
| 合計 | 8349tok | 5121tok |

資産あり側が +3228 tok（+63.0%）。
資産なし側は3事例すべて concern を返し、A/B/C を区別しなかった。

### この測定の交絡（重大）
合成リポジトリの `src/auth/permissions.py` の docstring に
「権限チェック。判断 DP-001 によりキャッシュしない。」と書いてあり、
判断そのものがコード内に漏れていた。ベースラインの理由文にこの docstring への
言及がある。したがって「資産なし」の対照群として成立していない。

### open questions
- 交絡を除いた場合、ベースラインは衝突を検出できるのか。
- トークン差は交絡を除いても残るのか。

### 反証の扱い
「判断資産を使えば必要な推論量が減る」という仮説は、この測定条件では成立しなかった。
プロジェクト方針（反証は成果であり、そこで打ち切る）に従い、仮説を通すための
実装変更は行わない。再測定は測定の妥当性を回復するためであり、結論を変えるためではない。

## 2026-09-21 判断資産あり/なしの比較（第2回、交絡除去後）

- source type: 自分で実行した測定
- source: `artifacts/reports/comparison.json`
- date: 2026-09-21
- 条件: 第1回と同じ。ただし合成リポジトリの docstring から
  「判断 DP-001 によりキャッシュしない」等の判断の漏れを除いた。

### fact（観測値）
| 事例 | 資産あり | 資産なし |
|---|---|---|
| A | inherit / 2248tok / 7.8s | concern / 2750tok / 22.5s |
| B | propose_update / 3398tok / 11.9s | concern / 4394tok / 38.0s |
| C | hold / 3868tok / 19.7s | concern / 2235tok / 19.7s |
| 合計 | 9514tok | 9379tok |

差 +135 tok（+1.4%）。第1回の +63.0% は交絡による見かけの差だった。

資産なし側は交絡除去後も3事例すべて concern。ただし理由文は具体的で、
事例Cでは「提案文は即時無効化を主張しているが差分には取得・格納のみ」と
主張と実装の食い違いを自力で指摘していた。

### interpretation（事実と分けて記す）
- **この測定が扱ったのは「単発レビュー1回分の推論コスト」だけである。**
  同一の問いに1回答えさせたとき、資産ありは削減を示さなかった（+1.4%、ほぼ互角）。
- **この結果を Reasoning Amortization 全体の否定に広げてはならない。**
  測っていないもの: 実装資産（動作確認済みコード）の再利用、開発完了までの複数工程、
  二回目以降の開発で省略される探索・比較・実装・検証。仮説はそれらを対象にしている。
- 差が出たのは分解能。資産あり側はA/B/Cを3通りに振り分け、
  なし側はすべて concern に潰した（次に何をすべきかが分かれない）。
- 事例Bでは、なし側が多く使って（4394tok）結論が曖昧だった
  （「衝突する可能性がありますが、その具体的内容は…」）。

### この測定の限界
- n=1。第1回と第2回で資産あり側も 8349 -> 9514tok と揺れており、
  プロンプト不変でも実行ごとの分散がある。反復測定をしていない。
- 資産なし側はLLMに1回尋ねるだけで、ツール反復もファイル探索も行わない。
  実際のコーディングエージェントの総コストとは異なる。
- 判断資産を人間が書くコストを計上していない。
- 合成リポジトリ1件・判断1件での結果。

### 結論（範囲を限定して記す）
単発レビューという条件では、推論量の削減を確認できなかった。
この条件に限り、経済的価値は主張しない。主張できるのは分解能の差のみ。

Reasoning Amortization の成否はこの測定では判定できていない。判定するには、
実装資産の再利用を含む「二回目の開発」を通した測定が必要であり、未実施である。

## 2026-09-21 実開発での Extractor 検証（reel-auto High-1）

- source type: 自分で実行した開発と、その記録
- source: `artifacts/experience/runs/run_reelauto_high1/`
- date: 2026-09-21

### fact（観測値）
実タスク: reel-auto のクロールフォールバックで Drive の appProperties からタグを拾う。
- 仕様書駆動ルールに従い design.md を先に更新（39.3.2 を追加、既存判断の後段のみ撤回）
- 実装: driveLedgerRead.ts に toLedgerImageFromCrawled を追加、index.ts の loadDriveImages を差し替え
- typecheck 通過。追加テスト7件すべて通過
- npm test 全体: 変更前 1897件中4件失敗 / 変更後 1904件中4件失敗（増えていない）
- Experience は 21 イベント、integrity 検証 OK

### 実開発でしか出なかった Extractor の欠陥 3件
1. **赤→緑の遷移に依存していた。** 実開発ではテストを先に失敗させないため遷移が0件になり、
   実装資産の検証根拠が空になった。合成事例では自分で赤を作ったため気づけなかった。
2. **パスを分類していなかった。** 仕様書(docs/design.md)を実装資産のパスとして拾い、
   applies_to に重複した glob が入った。
3. **対象リポジトリを取り違えた。** manifest.cwd は CLI を起動した場所であり、
   作業対象とは限らない。別リポジトリを操作したため repository/commit が
   AI HACK 側を指していた。

### 修正
1. ソース変更後に成功した実行を検証根拠とする。失敗したままのコマンドは
   `known_failing` として残し、根拠にはしない。
2. source / test / doc にパスを分類し、実装資産には source のみ使う。
3. `target_repo` note を明示記録する経路を追加。無い場合は shell の cwd から推定し、
   どちらで決めたかを `target.source` に残す。

### interpretation
合成事例だけでは Extractor の設計欠陥に気づけなかった。
「赤→緑」を検証根拠にする設計は、TDD を前提にしており普通の開発では成立しない。
実作業を1本通したことが、この3件を出した唯一の手段だった。

### open questions
- commit hash が `[要記述]` のまま。target_repo の明示記録は追加したが、
  今回の run では使っていないため未検証。二回目で確認する。
- 二回目(High-2)で、この候補が承認後に実際に引き当てられるかは未検証。

---

## 2026-09-22 連携アプリの判断を資産化した／条件の陳腐化を自動で検出した

### fact — DEC-004（連携アプリ側の判断を reel-auto へ先渡し）
- 連携アプリの認証設定に、実測付きの記録があった。ホスト信頼の環境変数を設定せず
  `next start` で起動したとき `GET /` が **200**（アプリ画面が表示）、`GET /api/posts` が **500**。
  認証ライブラリが Vercel 以外で Host を信頼せず例外を投げ、その例外が認証
  ミドルウェアを中断させ、フレームワークがページをそのまま返していた。
- reel-auto は Railway（Vercel 以外）に載る予定であり、**この前提の成立側に入る**。
- DEC-004 として資産化。フェーズ105 W3（アクセス制限）を task として評価した結果:
  - C1（デプロイ先が Vercel でない）= **supported**
  - C2（ミドルウェアの例外が「通す」側に倒れる）= **not_observed**（verifier=human）
  - C3（環境変数だけで認証を素通りさせる分岐が無い）= **supported**
  - 全体 = **hold**、human_review_required = true

### fact — DEC-003 の条件が自動で反転した
- task「台帳のフォルダ絞り込みを見直す」で評価したところ **propose_update**（exit 10）。
- 根拠: C1「台帳の取得列にフォルダ階層を辿れる列が含まれていない」（expectation: absent）が
  **contradicted**。`src/server/driveLedgerRead.ts:68` の `SELECT_COLUMNS` に
  `parent_folder_id` が入っている。これは DEC-003 を作った後の High-2 の作業で追加された列。
- 同じ run で DEC-001 と DEC-002 は inherit。全体は最も保守的な propose_update。

### fact — 使ったことで見つかった実装欠陥（file_exists）
- `_file_exists` が `observation.files_scanned` に**一致件数**を入れていた。
  判定側は `scanned == 0` を「探索していない」と解釈するため、
  **ファイルが存在しない場合が not_observed に落ち、`expectation: absent` の Condition が
  原理的に supported へ到達できなかった**。
- 実測: DEC-004 C1 が not_observed になった。修正後 supported。
- 修正: 探索単位である target 数を scanned とし、root がディレクトリでない場合のみ
  not_observed とした。回帰テスト2件追加（58件 → 60件、全通過。ruff 通過）。

### interpretation
- DEC-003 の件は、**判断が間違っていたのではなく、判断を支えていた前提が後の作業で変わった**
  形である。列が1つ増えたことで「階層を辿れない」という観測事実が崩れた。
  判定が `contradicted`（間違い）ではなく資産全体として `propose_update`（再検討せよ）に
  なったのは設計どおり。実際、親 id が1列増えても子孫の列挙はできないため、
  decision 自体は維持される可能性が高い。**そこを人に返すのが狙いの挙動。**
- これは計画して作った事例ではない。DEC-003 を書いた時点と、列を足した時点、
  そして今日それを踏む task が来た時点が別々にあり、その間の齟齬を自動で拾った。
- file_exists の欠陥は、**合成事例では expectation: absent を file_exists で書いたことが
  なかったために露出しなかった**。実際の判断（vercel.json が無いこと）を資産にした瞬間に出た。

### open questions
- DEC-003 は propose_update のまま。C1 の statement を
  「子孫を列挙できる手段が無い」に書き換えるのが妥当か、人の判断が必要（未実施）。
- DEC-004 C2 は Express では未確認。フェーズ105 W3 で認証方式を決めた時点で確認する。

---

## 2026-09-22 資産を実開発に適用した（reel-auto フェーズ105 W3）

### fact — 手渡しから実装までの経過
- `start p105-w3-auth` で DEC-004 を引き当て。判定 **hold**、human_review_required。
  手渡し資料 1,285 文字。C1 supported / **C2 not_observed（verifier=human）** / C3 supported。
- 手渡し資料の `governed_by` が「着手前に `§53.4`（対象外）を読め」と指示。
  読んだ結果 **「細かい権限制御はやらない。社内の人なら全プロジェクトを触れる前提で足る」**
  を確認し、利用者の識別が不要と判断して Basic 認証を選んだ（Google ログインを棄却）。
- C2 を人が実測した（Express 5.2.1、ミドルウェアで例外を投げる）:
  同期 throw → **500** / 非同期 reject → **500** / 正常 → 200。
- 実装は PR #10。`REEL_AUTH=off` の明示だけが認証を外し、資格情報未設定は **503**。
  実機で 8項目確認（`REEL_AUTH=OFF` が 503 に落ちることを含む）。認証下の実レンダリングも完走。

### fact — 資産の判断文が広すぎた
- DEC-004 の decision は「コードに固定する。環境変数には置かない」。
  適用してみると、**連携アプリの `DISABLE_AUTH=1` は省略時に閉じるので危険ではない**のに
  この文だと禁じてしまう。禁じるべきは「設定の省略が開く方向に倒れること」だった。
- 改訂案を **DEC-005（status: candidate = 未承認）** として作成し、
  `related_assets: DEC-004 relationship: supersedes` を張った。
- 同じ task で評価すると **DEC-004=hold / DEC-005=inherit**（全体は保守的に hold）。
  DEC-005 の C1〜C3 は3件とも supported で、**human 条件を含まないため自動で確定できる**。

### fact — 使ったことで見つかった実装欠陥（finish の検証実行）
- `finish --verify "npm run -s typecheck"` が **終了コード 254 = 失敗**と記録した。
  実際には通る。原因は `Recorder.resume` が `self.cwd` を `manifest.cwd`
  （= **CLI を起動した場所**。作業対象とは限らない）から復元し、
  `finish` が `rec.shell(cmd.split())` を cwd 未指定で呼んでいたこと。
  検証コマンドが reel-auto ではなく AI HACK 側で実行されていた。
- **Extractor で同型の取り違えを直したときに、検証コマンドの実行経路を見落としていた。**
- 修正: `rec.shell(cmd.split(), cwd=repo)`。構造pin の回帰テストを追加（58 → 61件）。
- 台帳は追記専用なので既存行は書き換えず、
  `p105-w3-auth-verify-recheck` として**訂正記録**を追記した（検証: 通過、assessment: matched）。

### interpretation
- **C（行動変化）が、今回は曖昧さなく観測できた。** 根拠は2つ。
  (a) `governed_by` の指示で `§53.4` を読み、そこに書かれた「権限制御は対象外」を根拠に
  Google ログインを棄却して Basic 認証を選んだ。資産が無ければ上流を読む理由が無かった。
  (b) 判断「省略時は閉じる」に従い、資格情報未設定を 503 にした。
  素直に書けば「資格情報が無ければ認証を省略する」= fail-open を選びやすい箇所である。
- **同時に、資産が間違っていた点も観測できた。** C2 は対象リポジトリで反転し、
  judgment は広すぎた。資産は「正しい知識の置き場」ではなく「検査にかけられる主張」として
  機能した。反転を捕まえたのは自動 verifier ではなく `verifier: human` の指示である。
- **偽の失敗を台帳に書いた**のは、この仕組みの信頼性に直結する欠陥だった。
  「落ちなかったことを成功とみなさない」と書いてあっても、**間違った場所で落ちていた**。

### open questions
- DEC-005 は未承認。承認するかは人の判断（承認すれば DEC-004 は superseded）。
- DEC-004 の C2 を retired にした判断が妥当か。Next.js 系へ適用する日には必要になる。

### fact — DEC-005 承認後の判定（2026-09-22）
- 人が DEC-005 を承認（`status: approved` / `approved_by: takeuchi`）し、
  DEC-004 を `superseded` にした（`related_assets: DEC-005 superseded_by`）。
- 通常検索の対象: DEC-001 / DEC-002 / DEC-003 / **DEC-005**。DEC-004 は除外。
- **同じ task（フェーズ105 W3 アクセス制限）を再評価すると `inherit`、
  `human_review_required` は false、`reuse_possible` は true。**
  C1〜C3 は3件とも supported。
- 承認前は `hold` / `human_review_required: true` だった（C2 が `verifier: human`）。

### interpretation
- **資産の改訂が、機械の判定を「常に人を待つ」から「自動で確定できる」へ変えた。**
  差は verifier の質である。DEC-004 の C2 は「フレームワークの既定挙動」を human に委ねており、
  対象リポジトリが変われば毎回人に返っていた。DEC-005 は同じ意図を
  「この実装がこう書かれているか」という grep 可能な条件3本に置き換えた。
- ここで一周した: 適用 → 判断文と前提の誤りが露出 → 候補として提案 → 人が承認 →
  旧版は superseded。**資産が「正しい知識」ではなく「検査にかけられて更新される主張」
  として扱えている。**
