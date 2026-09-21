# Claude Code `PreToolUse` フック — push をエージェントの手前で止める

## なぜ二層なのか

- **git フック（`scripts/hooks/pre-push`）** = git のアクションを止める層。
  誰が push しても（人間・CI・任意のエージェント）効く。ただし git が実際に
  push を試みた瞬間に止まるため、エージェントは「コマンドを打ってから」失敗を知る。
- **Claude Code `PreToolUse` フック** = Claude を止める層。
  Claude が Bash ツールで `git push` 等を **実行する前に** インターセプトし、
  ブロック（deny）またはユーザー確認（ask）に回す。エージェントがコマンドを
  走らせる前に止まり、ユーザーに可視化される。

両方入れることで「git レベルの一律ガード」と「エージェントを手前で止めて人間に
上げる」を同時に満たす。片方だけでは穴が残る（git フックだけ = Claude は打って
から気づく／PreToolUse だけ = 他の経路や CI は素通り）。

## settings.json スニペット

`.claude/settings.json`（またはプロジェクト共有の settings）に以下を追加する。
`git push`、および保護ブランチへの `git commit` を対象にした matcher。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'read -r payload; cmd=$(printf \"%s\" \"$payload\" | sed -n \"s/.*\\\"command\\\"[[:space:]]*:[[:space:]]*\\\"\\(.*\\)\\\".*/\\1/p\"); if printf \"%s\" \"$cmd\" | grep -Eq \"git[[:space:]]+push\"; then echo \"{\\\"decision\\\":\\\"ask\\\",\\\"reason\\\":\\\"Git 運用ガバナンス: push は PR 経由・保護ブランチ直 push / force 禁止。人間の承認が必要です。\\\"}\"; elif printf \"%s\" \"$cmd\" | grep -Eq \"git[[:space:]]+commit\" && git symbolic-ref --quiet --short HEAD 2>/dev/null | grep -Eq \"^(main|master|develop|integration|release)$\"; then echo \"{\\\"decision\\\":\\\"ask\\\",\\\"reason\\\":\\\"保護ブランチへの commit を検出。topic ブランチで作業してください。\\\"}\"; else echo \"{}\"; fi'"
          }
        ]
      }
    ]
  }
}
```

動作:

- Bash ツールの実行前に、ツール入力（JSON）を stdin で受け取り、`command`
  フィールドを取り出す。
- `git push` を含むなら `ask`（ユーザーに確認を求める）を返す。
- 現在ブランチが保護ブランチのときの `git commit` も `ask` を返す。
- それ以外は `{}`（介入なし）。

`ask` の代わりに `deny` を返せば確認なしで一律拒否になる。運用方針に合わせて選ぶ。

## 正直な注意

Claude Code の hooks の **設定スキーマ（キー名・返却 JSON の形・decision の
語彙）はバージョンによって変わりうる**。上記は考え方を示すサンプルであり、
導入前に必ず現行の公式ドキュメントで:

- `PreToolUse` の matcher 記法（ツール名の指定方法）
- フックへの入力ペイロード形式
- フックが返す JSON の decision キー（`ask` / `deny` / `allow` など）

を確認して整合させること。git フック（`pre-push`）は Claude のバージョンに
依存しない一次防衛線なので、まずそちらを確実に導入する。
