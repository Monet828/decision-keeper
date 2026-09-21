---
name: evidence-first-repro
version: v2
description: 調査で得た事実（facts）を、実装 agent 用の grounded かつデザインシステム固定の「機能再現」プロンプトに変換する contract author skill。事実だけを翻訳し、見た目は固定デザインシステムに PIN、実装後に挙動が事実からドリフトしていないか検証する。
---

# evidence-first-repro （v2）

## 目的と一言サマリ

競合・類似プロダクトの **機能（functionality）** について集めた **事実（facts）** を、別の実装 agent が実行して **プレーン・クイックな機能プロトタイプ** として再現できる **再現プロンプト（reproduction contract）** に変換する。そのプロトタイプを **人間が触って「使える / 違う」を経験ベースで判断** するための材料を作るのがゴール。

一言でいうと: **「事実だけを、解釈を混ぜずに、機能再現の実装命令へ翻訳する。見た目は固定デザインシステムに固定し、実装後に事実（挙動）からドリフトしていないか検証する。」**

この skill が守る規律は 3 つ:
1. 事実の抽出のみ。解釈・仮説・一般的な SaaS 論を混ぜない。
2. 事実をそのまま実装命令に変換する。
3. 出来上がった実装（挙動）が事実から逸脱していないか検証する。

---

## 何を作るのか — 機能再現であって視覚クローンではない（v2 で明確化）

**ゴールは FUNCTIONAL reproduction（機能再現）である。** 人間が実際に触って経験ベースで「使える / 違う」を判断できる、プレーンでクイックな機能プロトタイプを作る。

- **pixel-perfect な視覚クローンはゴールではない。** v1 に暗に含まれ得た「見た目そっくりに作る（visual clone）」モードは **v2 で明示的に廃止** する。
- 競合の source code は基本的に入手できない（SaaS はほとんど OSS 化されない）。ゆえに視覚クローンは技術的にも意味的にも狙わない。
- 再現するのは **機能・データ・流れ（インタラクション、状態遷移、フロー）** であって、見た目のリッチさではない。

この節は「誰かが再び visual-cloning を持ち込まない」ためのガードである。以降の設計はすべてこの前提に立つ。

---

## 第一原則: 忠実さは機能へ、プレーンさは見た目へ（v2）

> **「忠実さは "機能・データ・流れ" に振る。プレーンさは "見た目" に振る。」**
> = high-fidelity FUNCTION × low-decoration APPEARANCE。

再現の解像度は **機能・データ・流れ** に全振りし、見た目は装飾を削ってプレーンに保つ。二つは別々のターゲットを支配しているので、片方を上げてももう片方と競合しない。

固定のハウスデザインシステム（`assets/patterns/design-system/`）は **見た目を定数に PIN する** ことで、この原則を物理的に成立させる。これは二重の働きをする:

- (a) **毎回同じ見た目 → 低認知負荷。** レビューする人間は毎回同じ視覚言語だけを相手にし、判断を「機能が使えるか」だけに集中できる。
- (b) **facts-only ガードレール。** agent は固定キットから import して新しい style を書けないため、**物理的に「一般的で見栄えのいい SaaS dashboard」を作れない。** 見た目で事実の欠落をごまかせない。

**重要 — 矛盾しない:** 「デザインシステムで見た目を固定する」ことと「忠実に再現する」ことは衝突しない。両者は **異なるターゲット（機能 vs 見た目）** を支配しているからである。忠実さは機能側にだけ効き、固定は見た目側にだけ効く。

---

## この skill の役割 = contract author（Decision 1）

facts → prompt の変換は、それ自体が独立した役割 = **contract author（契約作成者）** である。これは research agent と implementation agent の **あいだ** に立つ工程であり、**この skill はその contract author そのもの**である。

親/子の位置づけ:

```
research agent   →   contract author (この skill)   →   implementation agent   →   （人間が触る）
（事実+source収集）      （事実→4層プロンプトへ翻訳）        （契約を実行するだけ）        使える/違う を判断
```

- この skill は **research agent ではない**（事実と source を集めるだけで synthesis はしない役割）。
- この skill は **implementation agent ではない**（契約を実行するだけの役割）。

### 鉄の掟（IRON RULE）

**contract author は新しい事実を一切足さない。** 行うのは純粋な翻訳のみ:
与えられた事実を 4 層プロンプト（Role / Facts / Implementation rules / Verification）に**組み替える**だけ。

- 実装対象（route・ファイル・module 境界）を **明示** することは許される。
- 事実に存在しない **機能的・挙動的なディテールを発明することは禁止**。

各境界は「no new information（新情報を足さない）」ゲートである:
- research → facts: 解釈を足さない
- facts → contract: 新しい事実を足さない ← **この skill の担当ゲート**
- contract → code: 契約の外のものを作らない

---

## 入力

この skill は 2 つの入力を受け取る:

1. **Research facts** — research agent が作った facts-sheet。各 fact には **source（URL / 原文引用 / スクリーンショット・録画）が必須**。source のない行は契約に載せない（`templates/facts-sheet.template.md` の hard gate）。事実は **behavior/flow 粒度**（トリガー → 動作 → 結果）で書かれている必要がある。
2. **Reproduction target** — 何を再現するか / どの module / どの route / **何を作らないか**。

source を持たない主張、および target に含まれない主張は、翻訳対象から除外する。

---

## 変換ルール（4層構造）

facts を、次の 4 層からなる 1 本の実装プロンプトに変換する:

1. **Role** — 誰として実行するか（{Codex|Claude Code}）、何を再現するか。機能再現であることを明示。
2. **Facts** — 「以下の事実だけを使う」宣言 + source 付き事実（behavior 粒度）の箇条書き。**ここに書かれた事実以外は使わせない。**
3. **Implementation rules** — 事実に限定する / 一般的な SaaS dashboard を発明しない / 固定デザインシステムからのみ import / route を到達可能にする / UI をこの module 固有に保つ / **プレーン&クイックでよいが facts に書かれた挙動は端折らず再現する**。
4. **Verification** — route が local で render する / build を通す / **facts に書かれた挙動（インタラクション・状態遷移・流れ）が実際に動く** こと（page が compile するだけでは不可）。

翻訳の際、事実 1 行がどの層のどの項目になるかを対応づける。**新しい行を発明しない。**

---

## デザインシステム固定（Decision 2）

見た目は **固定のハウスデザインシステム** に PIN する。LLM に look-and-feel を発明させない。（詳細は上記「第一原則」と `DESIGN-SYSTEM.md`。）

分業:
- **Facts = 機能 + データ + 流れ**（どの feature か / どのデータか / どの挙動・フローか）
- **デザインシステム = 見た目**（常に一定）

具体:
- TS 画面は 固定 UI キット + prototype shell から import する（bespoke CSS 禁止）。
- レポート / facts-sheet / 契約 は 固定の markdown/HTML テンプレートを使う。

---

## 出力形式

優先順位順:

1. **実装プロンプト（最優先）** — implementation agent にそのまま渡せる 1 本のプロンプト（`templates/reproduction-prompt.template.md` 準拠）。
2. **prompt contract** — 上記を mini-spec として `memory/contracts/` に置くための成果物。
3. **execution checklist** — 実装 agent が完了判定に使う確認項目（Verification 層の裏返し。挙動が動くことを含む）。

説明的なエッセイ、戦略論、ユーザーストーリーは出力しない。

---

## ワークフロー

1. **facts-sheet を受け取る/検証** — source 列が空の行を落とす。各 fact が behavior 粒度（トリガー → 動作 → 結果）かを確認し、「機能 X を持つ」レベルの弱い行は research agent に差し戻す。
2. **module 分割** — 事実を再現対象の module 単位に振り分ける（facts-sheet の `module` 列）。
3. **契約を書く** — 4 層プロンプトに翻訳。target route / import 元パス / 非対象を明示。挙動は端折らせない。
4. **implementation agent に渡す** — 契約を実行させる。
5. **local render + 挙動確認** — build して route が render し、facts の挙動が実際に動くことを確認。
6. **余計な UI を削る** — 事実にない要素（発明された dashboard 部品など）を削除させる。

---

## 使う表現 / 避ける表現

**使う:**
- 「Use only the facts below.（以下の事実だけを使う）」
- 「Import only from the design system at {path}.」
- 「Make the route reachable under {route}.」
- 「Plain & quick is fine; do not drop any behavior described in the facts.」
- 「Verify the behavior actually works, not just that the page compiles.」

**避ける:**
- 「generic SaaS dashboard」「analytics overview」「CRM-like」などの一般化された UI 語彙
- 「pixel-perfect」「visual clone」「そっくりに」等の視覚クローン指向
- 「おそらく」「一般的には」「ベストプラクティスとして」等の推測・解釈
- 事実にない機能・画面・指標を「あるとよい」として足すこと

---

## 判定基準（§11 — この skill の合否）

生成した契約が以下を満たすか:

1. **facts から変換されているか** — 各命令が source 付き事実に遡れるか（新事実ゼロ）。
2. **behavior 粒度で機能を再現させるか** — 「機能 X を持つ」ではなく「トリガー → 動作 → 結果」の挙動として命令できているか。
3. **agent 実装に使えるか** — そのまま実装 agent が実行して route が立ち上がるレベルの具体性か。
4. **UI っぽさでごまかしていないか** — 見栄えで事実の欠落を埋めていないか（固定 DS 縛りで担保）。
5. **対象/非対象の境界が明確か** — 何を作り何を作らないかが書かれているか。
6. **確認条件を含むか** — Verification 層（build / render / **挙動が動く** / 事実一致）があるか。

いずれか欠けたら契約を差し戻して書き直す。

---

## 生成物の置き場

- **再現契約（mini-spec）** → `memory/contracts/`（または `memory/tasks.md` から参照）。spec は memory/ に置くというテンプレートの規約に従う。契約は AGENTS.md / CLAUDE.md には置かない。
- **UI キット / デザインシステム** → `assets/patterns/design-system/`（再利用パターン置き場）。

---

## 背景：なぜこの設計か（prior art / grounding）

この設計は以下の検証済み先行研究・実践に依拠する（各クラスタ数行）。

**低忠実度プロトタイピング（「プレーン&クイックは "機能" を判定し "見た目" は判定しない」を裏づける）**
low-fidelity と high-fidelity のプロトタイプは、ほぼ **同じ** ユーザビリティ問題を surface する、という一連の知見。見た目の作り込みは判断材料の量をほとんど増やさない。
- Virzi, Sokolov & Karis 1996 (CHI): https://dl.acm.org/doi/10.1145/238386.238516
- Rettig 1994, "Prototyping for Tiny Fingers" (CACM): https://cacm.acm.org/opinion/prototyping-for-tiny-fingers/
- Sefelin, Tscheligi & Giller 2003 (CHI EA): https://dl.acm.org/doi/10.1145/765891.765986
- NN/g, lo-fi vs hi-fi: https://www.nngroup.com/articles/ux-prototype-hi-lo-fidelity/

**再現＝理解（reproduction-as-understanding）**
作れないものは理解していない、という立場。機能を再現できて初めて「わかった」と言える。
- Feynman, "What I cannot create, I do not understand": https://en.wikiquote.org/wiki/Richard_Feynman
- ML Reproducibility Challenge: https://reproml.org/

**競合 UX 分析 + スクリーンショット事実ライブラリ（facts-sheet の source を裏づける）**
競合のユーザビリティを一次資料（実画面・録画・スクショ）から評価・蓄積する実践。
- NN/g, Competitive Usability Evaluations: https://www.nngroup.com/articles/competitive-usability-evaluations/
- Mobbin: https://mobbin.com/

**Grounded / spec-driven generation（facts-only + prompt-as-contract を裏づける）**
外部の根拠に接地して生成する（RAG）／仕様を契約として生成を駆動する（spec-driven）。
- RAG, Lewis et al. 2020: https://arxiv.org/abs/2005.11401
- GitHub Spec-Kit / Spec-Driven Development: https://github.com/github/spec-kit

**正直な caveat:** 上記の一部ページは全文取得ではなく検索によるクロス照合で裏を取った。**一次確認済み（primary-confirmed）は低忠実度 3 本（Virzi 1996 / Rettig 1994 / Sefelin 2003）と RAG 論文（Lewis 2020）** である。それ以外は二次的な確認を含む。
