# review-no-hardcoded-config — 設定値の直書き禁止

## 根拠 (Basis)
URL・ホスト・ポート・ローカル絶対パスの直書きは環境依存を生み、移植・本番化を
壊す。設定は config / 環境変数で外出しする。

## 検査対象 (Target)
本番パスのソース・設定。**除外**: テスト、`*.example`、ドキュメント、
localhost を使う開発専用スクリプト。

## 規約 (Rule)
環境で変わる値をコードに埋め込まない。

```
❌ const base = "http://localhost:3000/api";
❌ const path = "/Users/alice/project/data.json";
❌ db.connect("192.168.1.10", 5432);
✅ const base = process.env.API_BASE_URL;
✅ const path = path.join(config.dataDir, "data.json");
```

## 検出方法 (Detection)
```sh
# ハードコードされた http(s) ホスト
grep -nE 'https?://(localhost|127\.0\.0\.1|[0-9]{1,3}(\.[0-9]{1,3}){3})(:[0-9]+)?' <files>
# ホスト:ポート / 生 IP:ポート
grep -nE '([0-9]{1,3}(\.[0-9]{1,3}){3}):[0-9]{2,5}' <files>
# ローカル絶対パス
grep -nE '(/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|[A-Za-z]:\\\\Users\\\\)' <files>
# 除外: テスト・*.example・docs・開発用 compose/スクリプト・コメント
#       env 参照済み（process.env.* / os.environ / config.*）は対象外
```

## 報告フォーマット (Report)
```
file:line — 設定値の直書き（<URL/パス/host:port>） — config/env へ外出し
```
