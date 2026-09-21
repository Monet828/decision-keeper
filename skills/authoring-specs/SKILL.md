---
name: authoring-specs
description: Fill in a spec with the user before writing product code. Use when the user describes something to build and no approved spec covers it, when a spec section is still blank or provisional, when the user changes requirements mid-implementation, or when measurement contradicts an approved spec. Covers the intake dialogue, the state markers, approval records under docs/approvals/, and the route back when a spec turns out wrong.
---

# 仕様策定

**承認済み仕様が無ければ、製品コードを書かない。**
読み取り調査・仕様整理・既存コードの確認は進めてよい。

雛形は `docs/templates/spec.md`。**運用ルールはその末尾に全部書いてある。**
このSkillはそれを繰り返さない。ここに書くのは、雛形を読む前に要る判断だけ。

## 守りたいものは2つあり、解き方が違う

| | 何を守るか | 手段 |
|---|---|---|
| **A 理解の担保** | ユーザーが理解していないものを土台にしない | 対話と状態マーカー |
| **B 逸脱の防止** | 承認していないものを実装に混ぜない | 承認記録とハッシュ照合 |

**片方を満たしても、もう片方は満たされない。**

## 入口

`./scripts/workflows/spec-first.sh new-spec <name>` で雛形が出る。
`status` が仕様と承認の対応を返す。

長いフォームへの記入を求めない。文章、箇条書き、参考資料、断片的なアイデア、
既存コード、どれからでも始める。

**最初にやることは質問ではなく整理。** 受け取ったものを自分の言葉で組み直して
提示し、そこから聞く。

## 発言と判断を混ぜない

| 区別するもの | 書き方 |
|---|---|
| ユーザーの発言 | そのまま引用する |
| AIの解釈 | 「〜と理解した」と明示 |
| AIの提案 | 「〜を提案する」と明示。行は `[候補]` |
| 承認された内容 | `[確定]`。承認記録にハッシュ付きで残す |

出典の追跡は、ユーザーが提示した資料（ファイル・URL・コード）に対してのみ。
会話ログへの逆参照は求めない。追跡できないなら「ユーザー発言に由来」とだけ書く。

## 既存プロジェクトへの後付け

既存実装を全部未承認扱いにすると、必須確認が常に停止する。

1. 導入時点で動いている機能・技術構成は **現状追認**。個別の承認記録を求めない
2. 既存の技術スタック・構造・制約を1文書に書き出し、ユーザーが承認する
3. **既存部分に変更を加える時点で、その範囲だけを仕様化する**

## 状態を落とさない

`memory/current-state.md` に最小限を残す。長い会話でこの仕組みが最初に壊れるのはここ。

**書く**: 承認を得た直後 ／ 段階が変わった直後 ／ セッションを終える直前
**読む**: セッション開始時と再開時 ／ 実装着手の直前

保持: 現在の段階・対象仕様のパスと版・承認済み範囲・ブロッカー・次の行動。
**仕様本文を複製しない。** 正本は `docs/specs/`。

## 停止条件

- 承認済み仕様が無いのに製品コードを求められた
- 要件の承認しかないのに技術構成の実装を求められた
- §8 に逃がせない未定が残っている
- 承認記録のハッシュと現在の仕様が食い違う
- **承認済み仕様と実測が矛盾した**（→ 雛形の「仕様どおりにできないと分かったら」）
- 委任範囲外の判断が必要になった
