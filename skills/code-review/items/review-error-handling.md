# review-error-handling — エラーの握りつぶし禁止

## 根拠 (Basis)
空の catch / except やエラー無視は、障害を隠して原因究明を不可能にする。
エラーは処理・再送出・記録のいずれかで扱う（黙って捨てない）。

## 検査対象 (Target)
全ソース。**除外**: テストの意図的な例外検証、明示コメントで無視理由を書いた箇所。

## 規約 (Rule)
catch/except を空にしない。エラー値を捨てない。

```
❌ try { risky() } catch (e) {}
❌ except Exception: pass
❌ _ = doThing()          // Go: エラーを _ で捨てる
✅ catch (e) { logger.error(e); throw new AppError(...); }
✅ except FileNotFoundError as e: logger.warning(...); raise
✅ if err != nil { return fmt.Errorf("do thing: %w", err) }
```

## 検出方法 (Detection)
```sh
# 空 catch (JS/TS/Java) — 波括弧内が空
grep -nE 'catch\s*\([^)]*\)\s*\{\s*\}' <files>
# Python: except ...: pass（同一行 or 直後）
grep -nE 'except[^\n:]*:\s*(pass)?\s*$' <files>
# Go: エラーを _ で捨てる代入
grep -nE '(^|[,(\s])_\s*[:=]{1,2}\s*[A-Za-z_].*\(' <files>
# 空 catch ブロック（次行が閉じ括弧のみ）は multiline で確認する
# 除外: コメントで理由明記のある箇所 / テストの例外検証 / re-raise を伴う except
```

## 報告フォーマット (Report)
```
file:line — エラー握りつぶし（空catch/pass/_破棄） — ログ or 再送出 or 明示的処理を追加
```
