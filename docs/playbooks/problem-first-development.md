# Problem-First Development

この playbook は、闇雲に開発せず、目的と問題を明確にしながら前進するための運用である。

## コアの考え方

- 実装は目的の代わりではない
- まず解くべき問題を明確にする
- 大問題を小問題へ分解する
- その時点で最重要の小問題を 1 つだけ選ぶ
- 進捗は「どれだけ書いたか」ではなく「どの問題を潰したか」で測る

## 推奨フロー

1. Concept
2. Goal
3. Biggest Problem
4. North Star
5. Necessary Conditions
6. Current Subproblem
7. Experiment / Implementation
8. Verification
9. Re-synthesis
10. Next Subproblem

## Concept

以下を短く説明する。

- 何を作りたいか
- 誰のためか
- なぜやるのか
- どんな体験や価値を作りたいか

## Goal

成果物ではなく、到達したい状態を書く。

## Biggest Problem

最初に解くべき最大問題を 1 つに絞る。

## North Star

North Star は機能名ではなく、解くべき問題の型として書く。

書く場所:

- `memory/decisions.md`

条件:

- 実装前に定義する
- 承認前は `assets/patterns/` を参照しない

## Necessary Conditions

North Star を必要条件へ分解する。

書く場所:

- `memory/tasks.md`

各 sub-goal には必ず以下を書く。

- これは North Star のどの必要条件を満たすか
- なぜ今この枝を潰すのか
- 終了条件は何か

## Current Subproblem

今潰す小問題は 1 つだけにする。

## Verification

確認すること:

- 本当にその小問題は潰れたか
- その小問題は North Star の必要条件に寄与したか
- 新しく見えた未確定事項は何か
- 次に進むべき小問題は何か

## Re-synthesis

分解した小問題を全部潰せば本当に North Star が解けるかを定期的に点検する。

見ること:

- 効かない枝を残していないか
- 必要条件の分解が漏れていないか
- すでに不要になった枝を早めに剪定できるか

## AI への依頼の仕方

以下の順で説明すると、AI が目的から逆算しやすい。

1. コンセプト
2. 目的
3. 現在の最大問題
4. North Star
5. 今回の current subproblem
6. 仮説
7. 確認したいこと
8. 今回やってほしい範囲
9. 止まるべき境界

## memory との接続

推奨:

- `docs/templates/PROBLEM-BRIEF.md` に長期の problem framing を置く
- `memory/problem-map.md` に現時点の problem decomposition を置く
- `memory/decisions.md` に North Star を置く
- `memory/tasks.md` に必要条件ツリーを置く
- `memory/sessions/` には、その日に潰す subproblem と未確定事項を置く
