# House Design System — spec / README

置き場: `assets/patterns/design-system/`

これは仕様書（README）であり実コードではない。実体（tokens / components）はこのディレクトリ配下に実装する。

## なぜ存在するか（Decision 2）

見た目を固定のハウスデザインシステムに PIN し、LLM に look-and-feel を発明させない。分業は明確:

- **Facts = 構造 + 挙動**（どの feature / どのデータ / どのフロー）
- **Design system = 見た目**（常に一定）

これは二重の役割を果たす:

1. **低認知負荷** — すべての出力レポートと、生成されるすべての TypeScript 画面が同じ見た目になる。読む側・レビューする側は毎回同じ視覚言語だけを相手にする。
2. **facts-only ガードレール** — 画面は固定キットから import して作るしかなく、新しい style を書けない。したがって agent は物理的に「一般的で見栄えのいい SaaS dashboard」を作れない。見た目で事実の欠落をごまかせない。

## 何を含むか

- **Design tokens** — color / spacing / typography。すべての見た目の唯一の source of truth。
- **UI component kit** — prototype 画面用のコンポーネント群（button, input, list, table, filter group など）。生成画面はここからのみ import する。
- **Prototype shell / layout** — 画面を載せる共通の外枠（header, container, route の受け皿）。
- **Fixed report template** — md / HTML ドキュメント（レポート・facts-sheet・契約）用の固定テンプレート。

## ルール

- **生成される TypeScript 画面は、この design system からのみ import する。** bespoke CSS / 新規 style を書いてはいけない。キットに無い要素は最も近い既存コンポーネントで代替する。
- **すべてのレポート系ドキュメントは report template を使う。** 自由書式のレイアウトを作らない。
- tokens / kit / shell を変更してよいのは design system のメンテナンス作業のみ。個別の再現プロンプト実行中に変更してはいけない。

## 想定フォルダ構成（sketch）

```
assets/patterns/design-system/
├── README.md                 # このファイル相当（運用ガイド）
├── tokens/
│   ├── color.ts
│   ├── spacing.ts
│   └── typography.ts
├── kit/                      # prototype 画面用 UI コンポーネント
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Table.tsx
│   ├── FilterGroup.tsx
│   └── index.ts              # 画面はここから import
├── shell/
│   ├── PrototypeShell.tsx    # 共通レイアウト / route の受け皿
│   └── index.ts
└── report/
    └── report.template.md    # レポート / facts-sheet / 契約の固定テンプレート
```
