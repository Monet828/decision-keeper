# Evidence Card

作業を**起票する前**に埋める。埋まらない項目があるなら、その作業はまだ着手できる
状態にない。

## いつ必須か

**過去ログ・メトリクスの集計、または DB の件数・棚卸しを根拠にする作業**では必須。
「◯◯件が重複している」「△△が××回失敗している」のような**観測値を前提に置く
作業**が該当する。

免除: ドキュメント/レビュー/調査方針などの非コード作業、typo 修正、既存挙動の
範囲内の小修正。

## なぜ必要か

観測時点・集計の意味論・反証条件を持たない主張が、そのまま作業の前提へ昇格するのを
防ぐため。前提が誤っていた場合、**その前提の上に積んだ作業はすべて無駄になる**。
起票前の5分で防げる。

---

## カード

```yaml
evidence_card:
  # 何を事実として主張しているか（1文）
  claim: ""

  # その観測・確認を行った日時、または commit / PR
  evidence_as_of: ""

  # 集計対象の期間、または DB snapshot。該当なしなら「該当なし」と明記する
  data_window: ""

  # 「件数」等の指標が raw / logical / effective のどれを指すか。
  # ここが最も事故りやすい（下の記入例を参照）
  semantic_definition: ""

  # 起票前に git log / merged PR / CHANGELOG / ADR を確認した結果を一行で。
  # 該当がなくても「確認したが該当変更なし」と明記する
  current_state_check: ""

  # この claim を反証する最も安い方法
  disconfirming_check: ""

  # 反証された場合、この作業をどう扱うか
  # （例: 調査で打ち切り、修正タスクは作らない）
  decision_if_false: ""
```

---

## 記入例（実際に手戻りになった起票）

「重複書き込みバグ」として起票され、調査の結果バグではなかった事例。
**`semantic_definition` と `current_state_check` の2項目で、起票前に止まっていた。**

```yaml
evidence_card:
  claim: >
    project が空の observation に重複書き込みが起きており、
    生 132 件 / 論理 77 件に水増しされている
  evidence_as_of: "2026-08-15 の調査レポート"
  data_window: "本番 DB snapshot 2026-08-15 時点、全期間"
  semantic_definition: >
    132 は raw row 数（deleted_at IS NULL のみ）、77 は supersedes を除外した
    logical 件数。異なる意味論の2値の差なので「重複」とは呼べない
    ← ここで claim が崩れる
  current_state_check: >
    backfill の実装と ADR を確認。元 row を更新せず修復 copy を append する
    正規動作であり、バグではない
  disconfirming_check: >
    supersedes / superseded_by を除外した logical view で数え直す（SQL 1本）
  decision_if_false: "調査で打ち切り。修正タスクは作らない"
```

## 反証されたときの扱い

> [!important] 反証は失敗ではない
> 誤った前提を潰したこと自体が成果である。**`decision_if_false` に従って打ち切る。**
> 反証された claim から follow-up の修正タスクを作らない。
>
> 作業者は、前提を反証した時点で**成功として報告してよい**。

報告には、確定した状態を添える。

```yaml
claims:
  - claim: "project 空の observation に重複書き込みがある"
    status: falsified          # confirmed | falsified | uncertain
    evidence: >
      330 組すべてが supersedes による backfill copy。
      raw と logical の混同だった
```

## 関連

- 調査そのものの手順 → `docs/playbooks/evidence-first-research.md`
- 集めた事実の記録先 → `memory/evidence-log.md`
