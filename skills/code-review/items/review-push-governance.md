# review-push-governance — push ガバナンスのバイパス検出

## 根拠 (Basis)
(1) の Git 運用ガバナンス（保護ブランチ直 push 禁止 / force 禁止 / PR 必須）を、
スクリプトや CI が **迂回**していないか検査する。フックで止めても、CI や
補助スクリプトに force push が書かれていれば骨抜きになる。

## 検査対象 (Target)
シェルスクリプト（`scripts/`、`*.sh`）、CI 定義（`.github/workflows/*.yml`、
`.gitlab-ci.yml` 等）、Makefile、package.json の scripts。
**除外**: 本アドオンの `governance/`（pre-push フック自身や説明文）、ドキュメント。

## 規約 (Rule)
スクリプト / CI に force push や保護ブランチ直 push を書かない。

```
❌ git push --force origin main
❌ git push -f
❌ run: git push origin HEAD:main      # CI から default へ直 push
✅ PR を作る（gh pr create ...）／人間が承認してマージ
```

## 検出方法 (Detection)
```sh
# force push フラグ
grep -nE 'git\s+push\b[^#\n]*(--force\b|--force-with-lease\b|\s-f\b)' <files>
# 保護ブランチへの直 push（main/master/develop/integration/release）
grep -nE 'git\s+push\b[^#\n]*\b(origin\s+)?(HEAD:)?(main|master|develop|integration|release)\b' <files>
# 破壊的操作の混入
grep -nE 'git\s+(reset\s+--hard|clean\s+-[a-z]*f|push\b.*--delete)\b' <files>
# 除外: governance/pre-push（フック実装）/ ドキュメントの ❌ 例示 / コメント行
#       ALLOW_PROTECTED_PUSH による人間の意識的上書きは設計上の抜け道（別途レビュー）
```

## 報告フォーマット (Report)
```
file:line — push ガバナンス迂回（<force / 保護ブランチ直 push / 破壊操作>） — PR 経由に是正、CI から除去
```
