---
name: reviewing-changes
description: Checklist and stance for reviewing code changes, covering what to look for (bugs, type safety, missing tests, security, responsibility leaks, over-engineering, performance, spec conflicts, stale docs) and how to report findings with evidence and a concrete fix rather than an opinion. Use when reviewing a diff, a pull request, or someone else's implementation.
---

# 変更のレビュー

## 姿勢

**実装者の意図を尊重する。** レビューの目的は書き直させることではなく、事故を防ぐこと。

**感想ではなく、根拠と修正案を出す。**

- ✗ 「ここは読みにくい」
- ✓ 「`parseConfig` が3箇所で異なる既定値を持つ（`a.ts:12`, `b.ts:40`, `c.ts:7`）。
  呼び出し側が既定値を仮定するとズレる。定数を1箇所に寄せるのが最小の修正」

## 見る観点

- **バグの可能性** — 特に境界値・空・null・並行実行
- **型安全性** — `any` / 不正な cast / 型では防げていない不変条件
- **テスト不足** — 変更した分岐にテストがあるか。落ちるはずのケースが通っていないか
- **セキュリティリスク** — 入力検証、パス、権限、秘密情報の露出
- **責務分離の崩れ** — 層をまたいだ知識の漏れ
- **過剰実装** — 使われていない抽象、将来のための汎用化
- **パフォーマンス上の問題** — 明らかな N+1、不要な同期処理
- **既存仕様との矛盾** — `docs/` と食い違っていないか
- **ドキュメント更新漏れ** — 挙動が変わったのに `docs/` が古いまま

## 指摘の優先順位

全部を同じ強さで言わない。**混ぜると重要な指摘が埋もれる。**

```text
1. 壊れる / 危険    → 必ず直す（バグ・セキュリティ・データ破損）
2. 仕様と矛盾       → 直すか、docs を更新するか決める
3. 保守性           → 直すことを推奨（根拠を添える）
4. 好み             → 言わないか、「好みだが」と明示する
```

## 「規約に書いてある」は強制ではない

文章の規約は破られる。**守らせたい制約は、型・テスト・フックで強制できないか**を考える。

- 「必ずこの検証を通すこと」と書く → 忘れられる
- 検証を通った値でないと関数を呼べない型にする → **コンパイルで止まる**

レビューで同じ規約違反を2回以上見たら、それは**強制する仕組みが無い**という信号。

## 自分が確認していないことを、確認したと書かない

- テストを実行していないなら「テストは通るはず」と書かない。
- 「動作確認済み」と書くなら、何をどう確認したか書く。
- 実行できなかった場合は、**その理由と代替の確認方法**を書く（`AGENTS.md` §4）。

## 関連

- 検証コマンド → `AGENTS.md` §4・`./scripts/loop/verify.sh`
- 判断を記録する → `skills/recording-decisions/SKILL.md`
