# Facts Sheet — {調査対象プロダクト / feature 名}

> 作成: research agent。この sheet は contract author（evidence-first-repro）への入力。
> **鉄則: source 列が空の行は再現プロンプトに載せない（source 列は hard gate）。**
> 事実のみを記録する。解釈・仮説・一般的な SaaS 論・推測された未実装機能は書かない。

## Reproduction target（再現対象）

- **再現するも（what to reproduce）**: {例: 検索結果ページのフィルタリング UI}
- **module**: {例: search-filters}
- **route**: {例: /prototype/search}
- **作らないもの（what NOT to build）**: {例: 認証・課金・一般的な dashboard・analytics・アカウント設定など、事実に現れない一切}

## Facts

各行は 1 つの観測可能な事実。source は URL または 原文引用（スクショの文言・DOM テキスト等）。

| # | fact | source (URL or 原文引用) | module |
|---|------|--------------------------|--------|
| _例1_ | _（例）フィルタは画面左に縦積みで、カテゴリ・価格帯・評価の 3 グループがある_ | _https://example.com/search（2026-07-01 閲覧）_ | _search-filters_ |
| _例2_ | _（例）価格帯フィルタは min/max の 2 つの数値入力で、適用ボタン押下時のみ結果が更新される_ | _原文引用: "Apply" ボタンのラベル、操作動画 00:12_ | _search-filters_ |
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

> 上の _例1 / _例2_ は書式サンプルであり、契約には含めない。

## 除外ログ（任意）

source を用意できず落とした主張をここに退避（後で source が付けば復活可）。

- {主張} — 理由: source 未確認
