# evidence-first-repro

競合・類似プロダクトについて集めた **事実（facts）** を、実装 agent が実行して feature を localhost prototype として再現する **再現プロンプト（reproduction contract）** に変換する skill。核となる規律: **事実だけを抽出し、解釈を混ぜず実装命令へ翻訳し、出来上がりが事実からドリフトしていないか検証する。**

## 3-role pipeline と "no new information" ゲート

この skill は 3 役割パイプラインの **真ん中** に立つ。各境界は「新しい情報を足さない」ゲート。

```
research agent            contract author (この skill)         implementation agent
事実 + source を収集   →   事実を 4 層プロンプトへ翻訳       →   契約を実行するだけ
（synthesis しない）        （新しい事実を足さない）              （契約の外を作らない）

     └── gate1 ──┘              └──── gate2 ────┘                └──── gate3 ────┘
   research→facts:            facts→contract:                  contract→code:
   解釈を足さない              新事実を足さない                  契約外を作らない
```

- **research agent** — 事実と source を集めるだけ。解釈・仮説・戦略論は書かない。
- **contract author（この skill）** — 与えられた事実を Role / Facts / Implementation rules / Verification の 4 層プロンプトに **組み替える** だけ。実装対象（route / file / module 境界）の明示は許されるが、事実にない視覚・挙動ディテールの発明は禁止（鉄の掟）。
- **implementation agent** — 契約を実行し、route を localhost で render させる。契約の外は作らない。

さらに見た目は固定ハウスデザインシステムに PIN される（Decision 2）: **Facts = 構造/挙動、Design system = 見た目**。これにより全出力の見た目が一定になり（低認知負荷）、agent が「一般的な SaaS dashboard」を発明できない（facts-only ガードレール）。

## 収録ファイルと AI_dev_template でのドロップ先

| ファイル | 役割 | AI_dev_template での配置 |
|---------|------|--------------------------|
| `SKILL.md` | skill 本体（contract author の運用手順） | `.claude/skills/evidence-first-repro/`（テンプレートの skill 置き場） |
| `templates/facts-sheet.template.md` | research 入力の書式（source が hard gate） | 上記 skill ディレクトリに同梱 |
| `templates/reproduction-prompt.template.md` | 実装 agent に渡す最終プロンプト | 上記 skill ディレクトリに同梱 |
| `DESIGN-SYSTEM.md` | 固定デザインシステムの spec/README | `assets/patterns/design-system/` |
| `README.md` | このファイル（全体像） | skill ディレクトリまたはリポジトリ内参照用 |

## テンプレートへの適合

- **生成される再現契約（mini-spec）は `memory/` に置く**（例: `memory/contracts/`、または `memory/tasks.md` から参照）。spec は memory/ に置くという規約に従い、AGENTS.md / CLAUDE.md には置かない。
- **UI キット / デザインシステムは `assets/patterns/design-system/`**（再利用パターン置き場）。
- 完了判定は Loop Engineering（`scripts/loop`）の verifier / step cap と整合する: 契約の Verification 層 = build と render が checklist になる。

## human-in-the-loop（重要）

**build / render が通ることは「compile できる」ことを証明するだけで、「事実に忠実である」ことは証明しない。** render 結果が facts と一致しているか（発明された要素が混ざっていないか）の **fidelity review は人間が行う**。機械検証は逸脱の入口を狭めるが、最終的な事実忠実性の確認は人手に残す。
