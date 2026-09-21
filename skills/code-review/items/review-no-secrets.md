# review-no-secrets — 秘密情報のハードコード禁止

## 根拠 (Basis)
API キー・トークン・秘密鍵をコードにコミットすると漏洩・悪用に直結する。
秘匿情報は環境変数 / シークレットマネージャで扱う（AGENTS.md セキュリティ規約）。

## 検査対象 (Target)
全ソース・設定ファイル。**除外**: `.env.example`、`*.sample`、テストの
ダミー値、ドキュメントの例示、ロックファイル・生成物・vendor/。

## 規約 (Rule)
鍵・トークン・秘密鍵を値として直書きしない。名前で参照し値は env から取る。

```
❌ const apiKey = "sk-Abc123RealLookingSecretValue";
❌ AWS_SECRET_ACCESS_KEY=AKIA....（.env をコミット）
✅ const apiKey = process.env.OPENAI_API_KEY;
✅ .env.example に OPENAI_API_KEY= だけ置く（値は空）
```

## 検出方法 (Detection)
```sh
# 代入形の疑わしいキー名
grep -nEi '(api[_-]?key|secret|token|passwd|password|access[_-]?key)[[:space:]]*[:=]' <files>
# 既知プレフィックスの実キー形
grep -nE '(sk-[A-Za-z0-9]{16,}|ntn_[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,})' <files>
# 秘密鍵ヘッダ
grep -nE 'BEGIN (RSA|EC|OPENSSH|PGP|DSA)? ?PRIVATE KEY' <files>
# 除外: .env.example / *.sample / __tests__ / *.test.* / *.spec.* / docs/ / プレースホルダ値
#       (例: "your-api-key", "xxxx", "changeme", 空文字, process.env.* 参照)
```

## 報告フォーマット (Report)
```
file:line — 秘密情報の直書き（<検出パターン>） — env 参照へ移し、値は履歴からも除去
```
