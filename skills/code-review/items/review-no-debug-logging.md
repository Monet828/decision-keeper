# review-no-debug-logging — 本番パスのデバッグ出力禁止

## 根拠 (Basis)
消し忘れたデバッグ出力はログ汚染・情報漏洩・性能劣化の原因。本番コードでは
構造化ロガーを使い、生の print/console は残さない。

## 検査対象 (Target)
本番パスのソース。**除外**: テスト、スクリプト（`scripts/`）、CLI ツール、
ロガー実装自体、生成物・vendor/。

## 規約 (Rule)
生のデバッグ出力を残さない。ロギングはプロジェクトのロガー経由。

```
❌ console.log("user", user);   ❌ print(f"debug {x}")   ❌ fmt.Println(resp)
✅ logger.debug("user loaded", { userId })   ✅ log.Debug("user loaded", ...)
```

## 検出方法 (Detection)
```sh
# JS/TS
grep -nE 'console\.(log|debug|dir|trace)\s*\(' <files>
# Python
grep -nE '(^|[^.\w])print\s*\(' <files>
# Go
grep -nE 'fmt\.Print(ln|f)?\s*\(' <files>
# Java/Kotlin
grep -nE 'System\.(out|err)\.print(ln)?\s*\(' <files>
# Ruby / PHP
grep -nE '(^|[^.\w])(puts|p|pp)\s|var_dump\s*\(|\bdd\s*\(' <files>
# 除外: テスト・scripts/・console.error / console.warn（意図的エラー通知は別判断）
#       ロガー定義ファイル・コメント行
```

## 報告フォーマット (Report)
```
file:line — デバッグ出力の残存（<関数>） — ロガー経由に置換 or 削除
```
