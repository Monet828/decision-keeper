---
name: delegating-to-codex
description: Delegate work to the OpenAI Codex CLI as a second execution backend with its own quota and its own model. Covers when delegation pays and the larger number of cases where it does not, the task contract to hand over, the report contract to require back, cross-review via `codex exec review`, parallel dispatch, and error recovery. Use when Claude's usage limit is the binding constraint, when a second model's review is wanted, or when a long investigation should run alongside other work.
---

# Codex への委譲

Codex は**別クォータ・別モデルの実行系**であって、Claude の代替ではない。
この skill は「いつ渡すか」「何を渡すか」「何を返させるか」を決める。

`codex` が PATH にあり `codex --login` 済みであること。無ければ委譲しない。

> [!important] 生の `codex exec` を叩かない
> `./scripts/codex/delegate.sh` と `./scripts/codex/review.sh` を使う。
> §3 が「機械的に決めろ」と書いている status / `files_modified` /
> コマンドの exit code は、そこで実装されている。手で叩くと**その3つが
> 委譲先の自己申告に戻り**、read-only 不変条件の検査と `</dev/null` も抜ける。

## 1. 委譲の判断

### 実測（3タスク × 3方式、2026-08-30）

| タスク | 自分で読む | Claude subagent | Codex |
|---|---|---|---|
| 21ファイル 1,215行 | 12,480 | **45,588** | **204,149** |
| 4ファイル 40KB | 11,512 | **50,257** | **164,926** |
| **1ファイル 110行** | **1,038** | **35,751** | **99,076** |

単位は消費トークン。太字は委譲先の内部消費。

> [!important] 委譲は「節約」ではなく「移転」
> Codex は同じ3タスクに **3.6倍**のトークンを使った（468,151 対 131,596）。
> 探索コマンドを何度も走らせるため。減るのは *Claude 側の*消費だけで、総量は増える。

### 振り分け

| 状況 | 送り先 |
|---|---|
| 1〜2ファイルの確認 | **自分で読む**（委譲は34〜95倍のトークンを払う） |
| context を節約したい | **Claude subagent**（親への返却は Codex とほぼ同じ。実測で差5ポイント） |
| **Claude の枠が逼迫・到達** | **Codex**（作業を止めないための退避） |
| **別モデルのレビューが欲しい** | **Codex**（§4） |
| **長時間かかり、並行して別作業をしたい** | **Codex**（§5） |
| 書き込みを伴う実装 | **委譲しない**（§6） |

**「念のため」「一応」では委譲しない。** 上の3つのどれかに当てはまるときだけ。

## 2. 渡す契約（task）

プロンプトに以下を書く。**書かないと Codex は埋めない。**

```text
[目的]     何を明らかにする / 何を作るか
[対象]     読んでよいパス。触ってはいけないもの
[報告形式] §3 の項目を明示的に列挙する
[反証条件] 「見つからなければ、無いと明言せよ」  ← 必須
[出典]     ファイルパスと行番号を要求する
```

`[反証条件]` を省くと**無いものをでっち上げる余地が残る**。実測でも、これを入れた
タスクでは「バグは見つからなかった」と正直に返ってきた。

### なぜ Codex に振ったかを残す

委譲を決めたら、その理由を一行で残す（`memory/sessions/` か作業ログ）。

```text
routing: codex / 理由: Claude 5h枠が80%超。read-only調査なので退避先として適切
```

後から「なぜこれは委譲したのか」を再構成できないと、振り分け規則を改善できない。

## 3. 返させる契約（report）

要約だけでは検証できず、全文を読むと節約が消える。**この中間を要求する。**

| 項目 | 誰が作るか |
|---|---|
| `status` | 終了状態から**機械的に**（`error` item の有無で判定しない。§7参照） |
| `files_modified` | **機械的に**。Codex の自己申告を使わない |
| `commands` + exit code | **機械的に**。テスト結果はここから読む |
| `summary` | Codex（3文以内） |
| `risks` / `unresolved` | Codex |
| `claims` | Codex（下記） |
| 詳細ログ | **パスのみ**。既定では読まない |

### claims — 反証は失敗ではない

判断を左右する主張を**最大3件**、状態つきで返させる。

```text
claim:    "重複書き込みが起きている"
status:   confirmed | falsified | uncertain
evidence: "330組すべて supersedes による正規動作。raw と logical の混同だった"
```

**`falsified` から修正タスクを作らない。** 誤った前提を潰したこと自体が成果であり、
そこで打ち切る。Codex が前提を反証して戻ってきたら、それは成功した委譲である。

> [!warning] 「テストが通った」を信じない
> Codex が通ったと書いていても、**自分で確認するまで通ったことにしない**
> （`AGENTS.md` §3 / §4）。委譲先の自己申告は「著者の主張」であって検証済みの
> 事実ではない。`commands` の exit code を見るか、自分で再実行する。

## 4. cross-review

専用サブコマンドがある。プロンプトを書く必要はない。

```bash
codex exec review --uncommitted     # 未コミットの変更
codex exec review --base main       # main との差分
codex exec review --commit <SHA>    # 特定コミット
```

**自分のレビューを終えた後に走らせる。** 先に走らせると自分の判断が引きずられる。

- **重なった指摘** → 確度が上がる。優先して対処
- **分かれた指摘** → 個別に判断。Codex が正しいとは限らない
- **Codex だけが挙げた指摘** → 自分が見落とした観点か、誤読か。根拠を確認してから採否

無条件に採用しない。§3 と同じで、これも「著者の主張」である。

## 5. 並列で投げる

独立した調査が複数あるときだけ。依存があるなら順に投げる。

```bash
codex exec --sandbox read-only --cd <repo> "調査A" > /tmp/a.md &
codex exec --sandbox read-only --cd <repo> "調査B" > /tmp/b.md &
wait
```

**投げたら統合するまでが一手。** 結果を並べて、矛盾があれば矛盾として記録する
（片方を黙って捨てない）。

### 続きから再開する

```bash
codex exec resume --last "<follow-up>"
codex exec resume <SESSION_ID> "<follow-up>"
```

新しいセッションを立て直すより安い。**同じプロンプトで再試行しない**（§8）。

## 6. 書き込みを伴う委譲

**やらない。read-only に留める。**

```bash
codex exec --sandbox read-only --cd <repo> "<task>"
```

`--sandbox read-only` を**必ず付ける**。実測で `files_modified` が0件になることを
確認済み。付け忘れると既定のサンドボックス設定が使われる。

書き込みを許すと、同じ作業ツリーを自分と Codex が同時に触る危険、中途半端な変更の
残留、ロールバック手段、diff の検証手順がすべて必要になる。read-only にはどれも要らない。

**どうしても必要になったら**: 専用の git worktree を切り、そこだけを書き込み可能に
する。`main` を Codex に触らせない。マージは人間が行う（`AGENTS.md` §9）。

## 7. 既知の落とし穴

- **固定オーバーヘッドが大きい。** 実測で `VERSION` 1ファイルを読ませただけで
  input 43,826 トークン（うち cached 22,272）。Codex 側の skill/plugin 定義が毎回載る。
  **軽いタスクほど割に合わない。** `~/.codex/skills/` の未使用 skill を無効化すると下がる。
- **初回が遅い。** 実測で初回 10.9秒、以降 4〜7秒。連続で投げる方が効率が良い。
- **`codex exec` は stdin を待って無限に止まる。** プロンプトを引数で渡していても、
  非対話の親プロセスから呼ぶと入力待ちに入る。実測で 6分40秒待っても返らなかった。
  **エラーではなくハングなので、失敗として検知できない。** 自動化するときは
  `</dev/null` を必ず付ける（`delegate.sh` は付けている）。
- **`error` item は失敗とは限らない。** "Skill descriptions were shortened" のような
  警告も `error` として出る。**`error` の有無で status を決めない。**
- **`~/.codex/config.toml` の `notify` を上書きしない。** ジョブごとに `-c notify=` を
  注入する third-party ツールがあるが、既存の連携を壊す。
- **`--output-schema <FILE>`** で最終応答を JSON Schema に従わせられる。要約を機械
  処理したいときだけ使う。

## 8. うまくいかないとき

| 症状 | 対処 |
|---|---|
| 見当違いの方向へ進んだ | **同じプロンプトで再試行しない。** 何が違ったかを足して投げ直す |
| 出力が長すぎる | ファイルへリダイレクトし、必要な箇所だけ読む |
| 途中で止まった | `codex exec resume --last` で続ける |
| 何度やっても失敗する | **タスクが大きすぎる。** 分割するか、自分でやる |
| 結果が信用できない | 委譲をやめる。検証コストが節約を上回っている |

**同じ失敗を3回繰り返したら、やり方が間違っている**（`skills/running-loops/SKILL.md`
の retry_budget と同じ判断）。

## 9. 発見と委譲を分離する（二層構造）

「1時間 Codex を使っていないのはもったいない」という発想は誤りである。
**Plus プランは使っても使わなくても同額**であり、稼働率を上げること自体には
価値が無い。むしろ委譲は3.6倍のトークンを使う（§1）ので、**軽い判断で
埋めようとすると損をする。**

価値があるのは「自分が確認しに行くつもりの無かった箇所を、実際に確認させる」
ことだった（実例: folder-lens の README が「機密ファイル判定は3箇所で
重複させない」と断言していたのに、検索経路だけが重複していた）。これは
**文書化された主張とコードの照合**という、範囲が閉じていて反証可能な形に
限れば安定して価値が出る。

そこで発見（いつ調べるか）と委譲（実際にCodexへ送るか）を分離する。
**時間駆動にするのは発見だけであり、委譲は常に人間駆動のままにする。**

```
scripts/codex/discover.sh   ← 定期実行（cron/launchd）。Codex を一切呼ばない
        ↓ 見つけた主張を memory/codex-queue.jsonl に積むだけ
scripts/codex/dispatch.sh   ← 人間が実行したときだけ Codex を呼ぶ
```

### discover.sh — 発見

`<!-- codex:verify -->` の直後の行を「検証すべき主張」として拾い、
`memory/codex-queue.jsonl` に積む。**Codex を呼ばない。** 主張の内容が変われば
（`file + 主張文` のハッシュが変わるので）新規として再度積まれ、変わらない
主張は二重に積まれない。cron/launchd で何分おきに回しても安全な理由はここにある。

マーキングの目安: `docs/` の `[x]`（実装済みと宣言している箇所）、`README.md`
の「このように動く」という断言、`AGENTS.md`/`CLAUDE.md` の不変条件。
**判断や設計方針にはマーカーを付けない。** 検証は事実の照合であって、
Codex に判断させる作業ではない（§3 と同じ理由）。

### dispatch.sh — 委譲

`--list` でキューを見る。`--next` で一番古い未処理を1件取り出し、
`delegate.sh` に照合タスクとして渡す。**ここで初めてクォータを使う。**
結果の `claims[0].status` をキューへ書き戻す（`confirmed` / `falsified` /
`uncertain`）。`falsified` は失敗ではなく成果である（§3 と同じ）。

### 常駐させる場合

discover.sh 自体は副作用が無い（読み取りとキューへの追記のみ）ので、
cron や launchd で回しても安全。**ただし委譲（dispatch.sh の実行）は
常駐化しない。** 自動発火は要らないという前提に立つなら、鳴らすのは
discover.sh の結果を人間に知らせるところまでで止める。

## 関連

- 委譲するか自分でやるかの前段 → `skills/session-bootstrap/SKILL.md`
- 受け取った指摘の扱い → `skills/reviewing-changes/SKILL.md`
- 事実と解釈を混ぜない原則 → `AGENTS.md` §3
