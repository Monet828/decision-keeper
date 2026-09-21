# Codex 発見デーモンの常駐設定（任意）

`scripts/codex/discover.sh` を定期実行するための手順。**`dispatch.sh` は
常駐させない** — 詳細と理由は `skills/delegating-to-codex/SKILL.md` §9。

discover.sh は読み取りとキューへの追記のみで、Codex を呼ばない。
安全に何度でも、どんな間隔でも実行できる。

## macOS（launchd）

`~/Library/LaunchAgents/com.local.codex-discover.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.local.codex-discover</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd /path/to/this/project &amp;&amp; ./scripts/codex/discover.sh</string>
  </array>
  <key>StartInterval</key>
  <string>1800</string>
  <key>StandardOutPath</key>
  <string>/tmp/codex-discover.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/codex-discover.err</string>
</dict>
</plist>
```

`StartInterval` は秒。`1800` で30分ごと。`/path/to/this/project` は絶対パスに置き換える。

```bash
launchctl load ~/Library/LaunchAgents/com.local.codex-discover.plist
launchctl unload ~/Library/LaunchAgents/com.local.codex-discover.plist   # 止める
```

## cron（Linux / macOS 共通）

```
*/30 * * * * cd /path/to/this/project && ./scripts/codex/discover.sh >> /tmp/codex-discover.log 2>&1
```

## 運用

- `./scripts/codex/dispatch.sh --list` で、いま溜まっている件数と内容を確認する
- 手が空いたときに `./scripts/codex/dispatch.sh --next` を叩く。**これだけが
  クォータを使う操作。**
- キューは `memory/codex-queue.jsonl`。壊れたら削除して構わない
  （`discover.sh` が再スキャンして作り直す。既に `confirmed`/`falsified` に
  なった項目の履歴だけが失われる）
