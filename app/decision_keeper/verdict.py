"""総合判定（R-04 / R-05 / R-06 / R-10）。

判定規則は決定論的であり、LLMに委ねない。
insufficient を最優先で見る。根拠不足を肯定にも否定にも倒さない。
"""

from __future__ import annotations

from .models import AssumptionJudgement, GuardFinding, Verdict


def decide(
    judgements: list[AssumptionJudgement], guard_findings: list[GuardFinding]
) -> tuple[Verdict, str]:
    """判定と、その理由を返す。"""
    if guard_findings:
        kinds = sorted({f.kind for f in guard_findings})
        return (
            "hold",
            f"検査を弱める変更を {len(guard_findings)} 件検出した（{', '.join(kinds)}）。"
            "テストの無効化・削除を前提維持の証拠として扱わないため、継承判定を出さない（R-10）。",
        )

    if not judgements:
        return "hold", "判定対象の前提が無い。"

    insufficient = [j for j in judgements if j.status == "insufficient"]
    disputed = [j for j in judgements if j.status == "disputed"]

    if insufficient:
        ids = "、".join(j.assumption_id for j in insufficient)
        return (
            "hold",
            f"根拠が不足する前提がある（{ids}）。不足を肯定にも否定にも倒さないため保留する（R-06）。",
        )

    if disputed:
        ids = "、".join(j.assumption_id for j in disputed)
        return (
            "propose_update",
            f"前提の変化が証拠付きで確認できた（{ids}）。判断の見直しを提案する。"
            "判断資産は書き換えない（R-05）。",
        )

    return (
        "inherit",
        "すべての前提が現在も成立している。過去の判断を継承し、衝突する変更を指摘する（R-04）。",
    )
