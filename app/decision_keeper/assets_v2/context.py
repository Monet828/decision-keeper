"""Engineering Context（原典§16）。

Asset Layer の責務は、現在の Engineering Context を**構造化して提供する**ところまで。
どのモデルを選択するかは Asset Layer の責務ではない（原典§16, EA-11）。
このモジュールにモデル名やモデル選択ロジックを置いてはならない。

選択は呼び出し側（Execution Agent / CLI）が、この Context を入力として行う。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .schema import AssetEvaluation

# 原典§16 が挙げる Engineering Context のフラグ
FLAGS = (
    "asset_found",
    "reuse_possible",
    "decision_conflict",
    "evidence_gap",
    "human_review_required",
)


class EngineeringContext(BaseModel):
    """OrcaRouter の Routing DSL などが入力として使える構造化された状況。"""

    asset_found: bool = False
    reuse_possible: bool = False
    decision_conflict: bool = False
    evidence_gap: bool = False
    human_review_required: bool = False

    asset_id: str = ""
    task_id: str = ""
    condition_count: int = 0
    supported_count: int = 0
    contradicted_count: int = 0
    insufficient_count: int = 0
    not_observed_count: int = 0
    reasons: list[str] = Field(default_factory=list)

    def to_headers(self) -> dict[str, str]:
        """HTTPヘッダー化する。Routing DSL が条件として使える形。"""
        headers = {
            f"X-Engineering-{name.replace('_', '-').title()}": ("1" if getattr(self, name) else "0")
            for name in FLAGS
        }
        headers["X-Engineering-Asset-Id"] = self.asset_id
        headers["X-Engineering-Conditions"] = str(self.condition_count)
        headers["X-Engineering-Contradicted"] = str(self.contradicted_count)
        return headers


def build(evaluation: AssetEvaluation | None) -> EngineeringContext:
    """AssetEvaluation から Engineering Context を組み立てる。決定論的。"""
    if evaluation is None:
        return EngineeringContext(
            asset_found=False,
            evidence_gap=True,
            reasons=["関連する Asset が見つからなかった"],
        )

    counts = {j: 0 for j in ("supported", "contradicted", "insufficient", "not_observed")}
    for ce in evaluation.condition_evaluations:
        counts[ce.judgment] += 1

    reasons: list[str] = []
    if evaluation.human_review_required:
        reasons.append("自動確認できない Condition を含む")
    if counts["contradicted"]:
        reasons.append(f"前提と観測が食い違う Condition が {counts['contradicted']} 件")
    if counts["insufficient"]:
        reasons.append(f"根拠が不足する Condition が {counts['insufficient']} 件")
    if counts["not_observed"]:
        reasons.append(f"観測できていない Condition が {counts['not_observed']} 件")
    if not reasons:
        reasons.append("すべての Condition が現在も成立している")

    return EngineeringContext(
        asset_found=True,
        reuse_possible=(evaluation.verdict == "inherit"),
        decision_conflict=(counts["contradicted"] > 0),
        evidence_gap=(counts["insufficient"] > 0 or counts["not_observed"] > 0),
        human_review_required=evaluation.human_review_required,
        asset_id=evaluation.asset_id,
        task_id=evaluation.task_id,
        condition_count=len(evaluation.condition_evaluations),
        supported_count=counts["supported"],
        contradicted_count=counts["contradicted"],
        insufficient_count=counts["insufficient"],
        not_observed_count=counts["not_observed"],
        reasons=reasons,
    )
