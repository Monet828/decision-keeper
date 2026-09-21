"""レポート生成（R-07）。Markdown と JSON を出す。

FACTS（観測した証拠）と INTERPRETATION（LLMの判定）を節として分ける。
推定と実測を区別し、固定応答（stub）で動いた場合はその旨を明示する。
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import EXIT_CODES, ReviewResult

VERDICT_LABEL = {
    "inherit": "継承（過去の判断は今も有効）",
    "propose_update": "更新提案（前提が変化している）",
    "hold": "保留（根拠が足りない、または検査が弱められている）",
}
STATUS_LABEL = {
    "supported": "支持された",
    "disputed": "矛盾した",
    "insufficient": "根拠不足",
}


def to_markdown(r: ReviewResult) -> str:
    lines: list[str] = []
    a = lines.append

    a(f"# 判断レビュー: {r.asset_id} (v{r.asset_version})")
    a("")
    a(f"## 判定: {VERDICT_LABEL[r.verdict]}")
    a("")
    a(r.verdict_reason)
    a("")
    a(f"終了コード: `{EXIT_CODES[r.verdict]}`")
    a("")

    a("## 資産の選定理由 (R-01)")
    a("")
    a(r.selection_reason)
    a("")

    if r.guard_findings:
        a("## 検査を弱める変更の検出 (R-10)")
        a("")
        a("前提の判定より前に指摘する。これらを前提維持の証拠として扱わない。")
        a("")
        a("| 種別 | ファイル | 行 | 該当 |")
        a("|---|---|---|---|")
        for f in r.guard_findings:
            a(f"| {f.kind} | `{f.path}` | {f.line or '-'} | `{f.excerpt}` |")
        a("")

    a("## FACTS — 収集した証拠 (R-02)")
    a("")
    a("決定論的なコレクタによる観測結果。LLMは関与していない。")
    a("")
    for e in r.assumption_evidence:
        a(f"### {e.assumption_id}: {e.statement}")
        a("")
        a(f"- 資産が期待する状態: `{e.expect}`")
        a(f"- 走査したファイル数: {e.scanned_files}")
        a(f"- 検出した証拠: **{len(e.evidence)} 件**")
        a(f"- コレクタの記録: {e.collector_note}")
        a("")
        if e.evidence:
            a("| ファイル | 行 | 該当 |")
            a("|---|---|---|")
            for ev in e.evidence[:10]:
                a(f"| `{ev.path}` | {ev.line or '-'} | `{ev.excerpt}` |")
            if len(e.evidence) > 10:
                a(f"| ... | | 他 {len(e.evidence) - 10} 件 |")
        else:
            a("証拠は **0 件**。走査した結果として0件であり、未調査ではない。")
        a("")

    a("## INTERPRETATION — 前提の判定 (R-03)")
    a("")
    a("| 前提 | 判定 | 理由 |")
    a("|---|---|---|")
    for j in r.judgements:
        a(f"| {j.assumption_id} | **{STATUS_LABEL[j.status]}** | {j.reason} |")
    a("")

    if r.conflicts:
        a("## 衝突する変更箇所 (R-04)")
        a("")
        a("| ファイル | 行 | 該当 |")
        a("|---|---|---|")
        for c in r.conflicts[:20]:
            a(f"| `{c.path}` | {c.line or '-'} | `{c.excerpt}` |")
        a("")

    if r.open_questions:
        a("## 判定に必要な追加確認 (R-06)")
        a("")
        for q in r.open_questions:
            a(f"- {q}")
        a("")

    a("## 実行記録 (R-07)")
    a("")
    if r.costs:
        a("| 工程 | モデル | 入力トークン | 出力トークン | 推定費用 | 所要秒 | 種別 |")
        a("|---|---|---|---|---|---|---|")
        for c in r.costs:
            cost = (
                f"{c.estimated_cost_usd:.6f} USD (推定)"
                if c.estimated_cost_usd is not None
                else "未算出"
            )
            kind = "固定応答(stub)" if c.is_stub else "実呼び出し"
            a(
                f"| {c.stage} | `{c.model}` | {c.prompt_tokens} | "
                f"{c.completion_tokens} | {cost} | {c.elapsed_sec:.2f} | {kind} |"
            )
        a("")
    else:
        a("LLM呼び出しは行われなかった。")
        a("")

    if any(c.is_stub for c in r.costs):
        a("> この実行は固定応答クライアントで動いている。"
          "判定品質の証拠にはならず、費用も発生していない。")
        a("")

    a(
        "- 判断資産の不変性 (R-05): "
        + ("確認済み（変更なし）" if r.assets_unchanged else "**変更が検出された**")
    )
    if r.limits_hit:
        a("- 上限による打ち切り (R-08):")
        for h in r.limits_hit:
            a(f"  - {h}")
    else:
        a("- 上限による打ち切り (R-08): なし")
    a("")

    a("## 限界")
    a("")
    a("- 合成データ1リポジトリでの結果であり、本番リポジトリでの有効性は示していない。")
    a("- 前提の判定はLLM出力に依存し、誤判定率は測定していない。")
    a("- テスト無効化の検出は正規表現によるもので、AST解析ではない。")
    a("")

    return "\n".join(lines)


def write(result: ReviewResult, out_path: Path) -> Path:
    """Markdown と、同名 .json を書く。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(result), encoding="utf-8")
    json_path = out_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json_path
