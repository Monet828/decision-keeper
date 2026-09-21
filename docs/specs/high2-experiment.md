# High-2 実験設計 — 資産が二回目の開発を変えるか

## 目的
North Star「一度の開発で得た Engineering Asset が、二回目以降の Execution Agent の
**実際の行動を変える**こと」を示す。token 削減そのものは目的にしない。

## 出発点
両群とも reel-auto/repo のコミット `a17ce40`（High-1 完了時点）から始める。
`git worktree` で隔離し、実リポジトリの作業ツリーを汚さない。

```
a17ce40（共通の出発点）
   ├─ /tmp/dk/wt/no-asset    (exp/high2-no-asset)    資産なし群
   └─ /tmp/dk/wt/with-asset  (exp/high2-with-asset)  資産あり群
```

## 群の違い
**タスク記述は両群で同一。** 差は「手渡し資料の有無」だけ。

- 資産なし群: `tests/fixtures/high2/task.md` のみ
- 資産あり群: 上記 ＋ `briefing.to_prompt()` の出力（DEC-001 / IMP-001 と
  条件の再検証結果、`entrypoint` が指す実コード、検証コマンド）

## 責務（案A）
| Execution Agent | LLM |
|---|---|
| どの資産を渡すか（Retrieval + Condition 再検証） | コードを書くこと |
| 実装資産の中身を読んで渡すこと | 移植元の特定 |
| 検証コマンドを実際に走らせること | 設計判断 |
| 行動の記録 | |

## 観測項目
**A. Retrieval** — High-1 由来の資産を発見できたか
**B. Applicability** — 鵜呑みにせず Condition を現在の状態で再検証したか
**C. Behavior Change**（最重要）— 資産なし群と比べて行動が変わったか
  - 読んだファイル数 / repo 探索の広さ
  - shell コマンド数
  - 移植元の特定に要した手数
  - **壊れた前提への反応**（後述）
  - 再利用した実装 / 採用した判断 / reject した資産
  - test までの経路
**D. Execution** — コード変更・test・verification まで実際に行ったか
**E. New Experience** — 結果を Experience として記録し、次の候補生成につながるか

従属指標として token / model call / wall time / cost も記録するが、
**これらを North Star の達成条件にしない。**

## 成否の判定
「エージェントが落ちなかった」を成功とみなさない。
指定した検証コマンドの終了コードで判定する（OrcaReplay の `--verify` と同じ立場）。

検証コマンド: `npx tsx --test tests/<対象>.test.ts` と `npm run typecheck`。
`npm test` 全体は High-1 時点で既に4件失敗しているため、合否判定には使わず
**変更前後で失敗数が増えていないか**だけを見る。

## この実験に埋め込まれた「壊れた前提」
High-2 のタスク記述は移植元として `~/Developer/Insta/repo/src/lib/sourceScope.ts` を
指名しているが、**このファイルは存在しない**（実測済み）。
実体は `composeQuery.ts` と `supabase/migrations/015_account_source_scope.sql`。

資産なし群はタスク記述を信じて探索することになる。
資産あり群は DEC-001 の C3（移植元の実在を実測で確認済み）を持っている。
**両群がこの矛盾にどう反応するかが、C の中心的な観測点。**

## 限界（先に書いておく）
- n=1。同一条件の反復は行わない
- 実行者は同一の LLM（私）であり、資産ありの内容を既に知っている。
  **資産なし群を「知らないふり」で実行することはできない。**
  この汚染は避けられないため、行動の差を主張するときは必ず併記する
- 合成ではなく実リポジトリだが、タスクは1件
