# Understand-First Development

既存コードベースを触るときは、先に「何を変えるか」ではなく「何を理解したか」を明示する。

## 目的

- 誤解した責務の上に実装を積まない
- 影響範囲を把握しないまま修正しない
- 読んだ内容と未解決事項を再利用可能な形で残す

## 最低限やること

1. 対象領域を決める
2. 関連する `src/`、`tests/`、`docs/`、`memory/` を読む
3. `memory/understanding-map.md` を更新する
4. `Unknowns` と `Safe change boundary` を書く
5. 必要なら `memory/sessions/` にも未解決事項を残す

## understanding-map に書くこと

- Target
- Why this area matters
- Files read
- Related docs
- Related decisions
- Current behavior
- Responsibilities
- Inputs / Outputs
- Dependencies
- Risks
- Unknowns
- Assumptions
- Safe change boundary
- Next reading target
- Resume From

## 実装前チェック

- 読んだファイルが列挙されているか
- 現状挙動を自分の言葉で説明できるか
- 安全に触れる境界が書けているか
- 不明点が記録されているか

これらが満たせない場合は、実装より先に追加読解を行う。
