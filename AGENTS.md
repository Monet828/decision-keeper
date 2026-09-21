# AGENTS.md

Claude Code、Codex、その他AIエージェントがこのリポジトリで作業する際の共通ルール。
AIは設計・実装・レビュー・記録を支援する開発メンバーとして扱うが、**最終判断は人間が行う**。

このファイルは毎ターン context に載る。**破ると事故る規約だけ**をここに置き、手順書は
`skills/` に置いて必要な時だけ読む。詳細な手順が要るときは、下表の skill を読むこと。

## 手順書の所在（必要時のみ読む）

| いつ | 読むもの |
|---|---|
| 作業を開始する / 再開する / 迷って止まった | `skills/session-bootstrap/SKILL.md` |
| `memory/` を更新する / 昇格を判断する | `skills/managing-memory/SKILL.md` |
| 設計判断を記録する | `skills/recording-decisions/SKILL.md` |
| コードをレビューする | `skills/reviewing-changes/SKILL.md` |
| 長時間・複数セッションの作業を回す | `skills/running-loops/SKILL.md` |
| Claude の枠が逼迫、または別モデルにレビューさせたい | `skills/delegating-to-codex/SKILL.md` |

## 1. 正本の順序

- `docs/` = 正式仕様（正本）、`memory/` = 作業記憶。**矛盾したら `docs/` を優先**する。
  ただし現在の作業状況は `memory/current-state.md` を見る。
- ディレクトリの役割は `docs/project-structure.md` を唯一の正とする。
- Claude Code / Codex の**内部記憶を正本にしない**。正本は
  `AGENTS.md` / `memory/current-state.md` / `memory/decisions.md` / `docs/` / `src/`。
  ツール固有設定は `.claude/` `.codex/` に置くが、共通ルールは本ファイルが優先。

## 2. 実装の作法

- 実装前に、目的・影響範囲・変更対象ファイル・リスクを確認する。
- 既存設計に反する変更をするときは、実装前に理由と代替案を提示する。
- 既存の責務分離・コードスタイルを壊さない。不要な抽象化を足さない。
- 変更は小さく分ける。**ついでの大規模リファクタリングをしない**。
- 推測で実装しない。不明点は仮定として明示する。
- 影響範囲が想定より広がったら、作業を止めて方針を確認する。

## 3. 事実と解釈を混ぜない

調査・比較では、最初から主観的な評価やおすすめを混ぜない。

- まず一次情報・公式ドキュメント・観測事実・出典・日付を整理する。
- **事実と解釈を分けて書く**。不明点と要確認点を明示する。
- 解釈・採用判断・意味づけを求められた場合のみ、事実の後段として書く。
- 自分で確認していないことを、確認した事実として書かない
  （「著者の主張」と「自分で検証した事実」を区別する）。

## 4. 検証

変更後は、必要に応じて型チェック・Lint・Unit test・Integration test・Build・手動確認を行う。

- `./scripts/loop/verify.sh` が設定済みのテスト/lint/buildを検出して実行する。
  未設定項目は `[SKIP]` として明示され、**成功扱いにはならない**。
- テストを実行できなかった場合は、**その理由と代替の確認方法を明記**する。
- 完了とみなす前に、少なくとも一度は verifier 観点で見直す。

## 5. 大きな出力は context に流し込まない

context window は共有資源であり、一度入れたものは会話が続くかぎり残り続ける。

- **長い出力はファイルへ退避し、必要な箇所だけ読む。**
  ログ・全文検索結果・巨大な JSON・ビルド出力・`git log` の長い履歴などは、
  `> /tmp/<name>.txt` に落として `grep` / `sed -n` で該当箇所だけ取る。
- **失敗した実行は末尾から読む。** 成功したコマンドの全出力は要らない。
- **探索は subagent に委ねる。** 「どこにあるか分からないものを探す」作業は
  往復が多く、その全部が context に残る。subagent なら**結論だけが返る**
  （実測: 21ファイルの調査で内部 45,588 トークン、親へは約 2,000）。
- 何をどこへ退避したかは述べる。**黙って捨てない。**

## 6. 標準コマンド

利用可能なら以下を標準とする（未実装なら追加時に本節を更新）。

`./install.sh` / `./run.sh` / `./scripts/setup/bootstrap.sh` / `./scripts/setup/doctor.sh` /
`./scripts/hooks/{pre-task,post-task,stop,save-memory}.sh` /
`./scripts/loop/verify.sh`（実チェック。`[PASS]/[SKIP]/[FAIL]`）/
`./scripts/loop/record-verification.sh`（自己申告ログ。verify.sh 実行後に記録）/
`./scripts/loop/resume.sh` /
`./scripts/codex/delegate.sh`（Codex への read-only 委譲。**生の `codex exec` を叩かない**）/
`./scripts/codex/review.sh`（別モデルによるレビュー）/
`./scripts/codex/discover.sh`（文書化された主張を検証キューへ積む。Codex を呼ばない）/
`./scripts/codex/dispatch.sh`（キューから1件取り出し、人間が実行したときだけ Codex に委譲する）

## 7. 禁止事項

- 明示されていない大規模リファクタリング
- 不要なファイルの大量生成
- 仕様の暗黙変更
- テストを無視した実装
- `docs/` と矛盾する変更
- セキュリティ上危険なショートカット
- 秘密情報のログ出力
- **一時的な推測を正式仕様として記録すること**

## 8. 停止すべき境界条件

合意された目的と範囲の中では自律的に進めてよい（詳細は
`skills/session-bootstrap/SKILL.md`）。ただし以下に達したら**止まって人間に確認する**。

- 目的が曖昧で、解釈により成果物が大きく変わるとき
- 合意済みの範囲を超える変更が必要になったとき
- 新しい仕様決定・アーキテクチャ判断が必要になったとき
- **破壊的変更・不可逆操作・大規模リファクタリング**が必要になったとき
- **本番影響・認証・課金・権限・秘密情報**に関わるとき
- 妥当な検証手段がなく、安全に完了とみなせないとき
- **`delegate.sh` が exit 3 を返したとき**（read-only のはずが変更が出た）。
  返ってきた内容を信用せず、止まって報告する

## 9. Git 運用ガバナンス

> [!important] この節は prose だけでは守られない
> 文章の規約は「お願い」であり、モデルは無視しうる。だから二層で担保する。
> **お願いの層** = 本節。**ハードストップの層** = `scripts/hooks/pre-push` と
> Claude Code の `PreToolUse` フック。強制はフックが担う。

- 全ての変更は **Pull Request 経由**で人間のレビューに出す。人間の明示承認なしに
  保護ブランチへ反映しない。
- **保護ブランチへの直接 commit / push を禁止**する（default / integration / release）。
  default は `git symbolic-ref --quiet --short refs/remotes/origin/HEAD` で自動検出。
  作業は必ず topic ブランチで行う。
- **`--force` / `-f` の push を禁止**する。`reset --hard` / `clean -f` /
  ブランチ強制削除などの破壊的操作は、**人間の明示指示があるときのみ**実行する。
- **無言 push を禁止する**。push 前に「何を・どのブランチへ・なぜ」を人間に告げ、
  PR を開く。push だけして黙る／PR を作らずに push する、は違反。
- **完了時は「PR を開いて人間に引き渡して停止」**する。マージ・リリースタグ付け・
  本番デプロイは人間の担当であり、エージェントは行わない。
- 導入: `scripts/hooks/install-hooks.sh` / 詳細:
  `docs/playbooks/git-governance-pretooluse.md`


## Spec-First Development Addon

**実装前に、承認済み仕様があることを確認する。** 無ければ製品コードを書かない。
読み取り調査・仕様整理・既存コードの確認は進めてよい。

仕様は1ファイル。`docs/specs/<name>.md`。雛形と運用ルールは
`docs/templates/spec.md` にまとまっている。**ここには書かない**
（毎セッション読まれる場所を膨らませない）。

仕様を書いている間は、応答の最後に毎回この3行を出す。
**気を利かせて指摘するのではなく、機械的に列挙する。**

```
空欄: §3, §6
候補のまま: R-02, R-05
未定で進行中: 画像形式の決定（§8）
```

次のいずれかに当たったら、`authoring-specs` Skill を読む。

- 承認済み仕様が無い／今回の作業が承認範囲の外
- 要件の承認しかないのに技術構成の実装を求められた
- `[候補]` が残っている（§8 に逃がせないもの）
- 承認記録のハッシュと現在の仕様が食い違う
- **承認済み仕様と実測が矛盾した**（黙って実装で回避しない）
- 実装中に要件が変わった（**例外ではない。通常の経路**）

「いいね」「なるほど」「よさそう」および無返答は**承認ではない**。
対象・範囲・版を明示して承認を求め、`docs/approvals/` に記録する。

**AIが書いた行は必ず `[候補]` から始まる。** ユーザーが同意して初めて `[確定]`。
実装とテストには、由来する要件IDを記す（適合検査が列挙する）。
状態は `./scripts/workflows/spec-first.sh status` で見る。


## Understand-First Development Addon

このプロジェクトでは、既存コードや既存仕様を触る前に、まず対象を理解する。

基本方針:

- 既存コードを変更する前に、関連する実装、`docs/`、`memory/` を読む
- 実装に入る前に、対象領域の責務、入出力、依存関係、影響範囲を言語化する
- 理解した内容は `memory/understanding-map.md` に残し、chat のみに留めない
- 未解決事項がある場合は `memory/sessions/` の `Unresolved / Open Questions` にも残す

推奨運用:

- `memory/understanding-map.md` に対象、読んだファイル、現状挙動、責務、依存関係、リスク、unknowns を残す
- `scripts/workflows/understand-first.sh` を使って理解 checkpoint を残す
- 大きい変更では `Safe change boundary` を書いてから実装へ進む

停止条件:

- 対象責務を説明できない
- 主な入口と出口が分からない
- 影響範囲の仮説が持てない
- 未解決事項が多く、安全に変更できる境界が引けない

軽微な修正では簡略化してよいが、`Files read` と `Unknowns` を空で進めない。


## Evidence-First Research Addon

このプロジェクトでは、調査や比較を行うとき、最初から主観的な評価やおすすめを混ぜない。

基本方針:

- 最初に一次情報、公式情報、観測事実を整理する
- 出典、日付、引用または要約を `memory/evidence-log.md` に残す
- 事実と解釈を分けて書く
- 不明点と確認が必要な点を明示する

観測値を前提に置く作業（過去ログ・メトリクスの集計、DB の件数・棚卸しを根拠に
するもの）は、**起票前に Evidence Card を埋める**。埋まらない項目があるなら、
その作業はまだ着手できる状態にない。テンプレートは `docs/templates/evidence-card.md`。

- 「件数」が raw / logical / effective のどれを指すかを必ず定義する。ここが最も
  事故りやすい
- その主張を**反証する最も安い方法**と、**反証されたら作業をどう扱うか**を先に書く
- **反証は失敗ではない。** 誤った前提を潰したこと自体が成果であり、そこで打ち切る。
  反証された claim から follow-up の修正タスクを作らない

推奨運用:

- `memory/evidence-log.md` に source type、source、date、fact、quote or summary、open questions を残す
- `scripts/workflows/evidence-first.sh` を使って調査 checkpoint を残す
- 調査途中の仮説は正式仕様として昇格させず、まず evidence として整理する

停止条件:

- 主張の根拠となる source が示せない
- source date が不明で、鮮度が重要な論点を安全に扱えない
- 事実と解釈が混ざっていて、あとから検証できない

比較や提案を求められた場合のみ、evidence の後段として解釈を書く。


## Problem-First Development Addon

このプロジェクトでは、実装を急ぐ前に、まず解くべき問題を明確にする。

基本方針:

- コンセプト、目的、最大問題を先に言語化する
- 実装に入る前に、解くべき一番大きな問題を 1 つだけ `memory/decisions.md` に North Star として定義する
- 大問題を小問題へ分解する
- その時点で最重要の小問題を 1 つだけ選ぶ
- 進捗は、書いた量ではなく、潰した問題で評価する

推奨運用:

- `docs/templates/PROBLEM-BRIEF.md` に長期の problem framing を置く
- `memory/problem-map.md` に current problem decomposition を置く
- `memory/tasks.md` には必要条件ツリーを置き、各 sub-goal に North Star との traceability を書く
- `memory/sessions/` には、その日に潰す current subproblem と unresolved questions を置く
- `scripts/workflows/problem-framing.sh` を使って問題設定の checkpoint を残す

ルール:

- `memory/decisions.md` に North Star が定義・承認されるまで `assets/patterns/` を参照しない
- issue が確定した後にだけ、`assets/patterns/` の `When To Apply / When Not To Apply` で適合性を確認する
- 各 sub-goal は 1 loop として進め、完了を主張する前に verifier で「本当に効いたか」を検証する
- verifier では「この枝を全部潰したら本当に North Star が解けるか」を再合成の観点で点検する
- 効いた解法は `assets/patterns/` に新規追加するか、既存 pattern の `Pitfalls / Learnings` を更新する
