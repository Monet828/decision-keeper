"""AgentResult の Markdown / JSON 出力。

Observation（Evidence）と Interpretation（ConditionEvaluation）を節として分ける（原典§7）。
"""

from __future__ import annotations

import json
from pathlib import Path

from .agent import AgentResult

VERDICT_LABEL = {
    "inherit": "継承（過去の判断は今も有効）",
    "propose_update": "更新提案（Conditionが変化している）",
    "hold": "保留（根拠不足・未観測・人の確認が必要）",
}
JUDGMENT_LABEL = {
    "supported": "支持された",
    "contradicted": "食い違った",
    "insufficient": "根拠不足",
    "not_observed": "観測できていない",
}


def to_markdown(r: AgentResult) -> str:
    lines: list[str] = []
    a = lines.append
    e = r.evaluation

    a(f"# Asset Evaluation: {r.task_id}")
    a("")
    if e is None:
        a("## 判定: 関連する Asset が見つからなかった")
        a("")
    else:
        a(f"## 判定: {VERDICT_LABEL[e.verdict]}")
        a("")
        a(e.verdict_reason)
        a("")
        a(f"終了コード: `{r.exit_code}`")
        a("")

    c = r.engineering_context
    a("## Engineering Context")
    a("")
    a("Asset Layer は状況を構造化して提供するところまでを担う。")
    a("どのモデルを使うかはここでは決めない（原典§16）。")
    a("")
    a("| フラグ | 値 |")
    a("|---|---|")
    for name in ("asset_found", "reuse_possible", "decision_conflict",
                 "evidence_gap", "human_review_required"):
        a(f"| `{name}` | {'true' if getattr(c, name) else 'false'} |")
    a("")
    for reason in c.reasons:
        a(f"- {reason}")
    a("")

    for ev in r.evaluations:
        a(f"## Asset {ev.asset_id} v{ev.asset_version} — {ev.verdict}")
        a("")
        a(ev.selection_reason)
        a("")
        a("### FACTS — Evidence（観測事実）")
        a("")
        for evi in ev.evidence:
            a(f"**{evi.id}** (`{evi.type}`)")
            a("")
            a(f"- 観測: `{json.dumps(evi.observation, ensure_ascii=False)}`")
            if evi.query:
                a(f"- 問い合わせ: `{json.dumps(evi.query, ensure_ascii=False)}`")
            if evi.samples:
                a("")
                a("| ファイル | 行 | 該当 |")
                a("|---|---|---|")
                for smp in evi.samples[:10]:
                    a(
                        f"| `{smp.get('path', '-')}` | {smp.get('line', '-')} "
                        f"| `{smp.get('excerpt', '')}` |"
                    )
            a("")
        a("### INTERPRETATION — ConditionEvaluation（判定）")
        a("")
        a("| Condition | 判定 | 根拠Evidence | 理由 |")
        a("|---|---|---|---|")
        for ce in ev.condition_evaluations:
            a(
                f"| {ce.condition_id} | **{JUDGMENT_LABEL[ce.judgment]}** | "
                f"{'、'.join(ce.evidence)} | {ce.reason} |"
            )
        a("")

    a("## Implementation Asset の再利用可否")
    a("")
    if r.reusable_implementations:
        a("再利用可: " + "、".join(f"`{i}`" for i in r.reusable_implementations))
    else:
        a("再利用可: なし")
    if r.blocked_implementations:
        a("")
        a("再利用しない: " + "、".join(f"`{i}`" for i in r.blocked_implementations))
    a("")

    if r.notes:
        a("## 注記")
        a("")
        for n in r.notes:
            a(f"- {n}")
        a("")

    a("## 確認")
    a("")
    a(f"- Approved Asset の不変性 (EA-03): "
      f"{'確認済み（変更なし）' if r.assets_unchanged else '**変更が検出された**'}")
    a("- 実装資産の適用とテスト実行は今回の範囲外（§18）")
    a("")
    return "\n".join(lines)


def write(result: AgentResult, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(result), encoding="utf-8")
    json_path = out_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json_path
