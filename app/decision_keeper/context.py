"""Engineering Context の算出とモデル選択。

決定論的に集めた証拠から「この判定がどれだけ難しいか」を先に決め、
それに応じて OrcaRouter へ渡すモデルを切り替える。

OrcaRouter が「この推論をどのモデルで行うか」を担うのに対し、
ここは「そもそもどれだけ強い推論が要るか」を証拠から決める層である。
難度の算出に LLM は関与しない。
"""

from __future__ import annotations

from .models import AssumptionEvidence, EngineeringContext, GuardFinding

# 難度ごとの既定モデル。CLIで上書きできる。
DEFAULT_MODEL_LOW = "deepseek/deepseek-v4-flash"
DEFAULT_MODEL_HIGH = "anthropic/claude-sonnet-5"


def compute(
    asset_id: str,
    evidence: list[AssumptionEvidence],
    guard_findings: list[GuardFinding],
    claimed_flags: dict[str, bool],
) -> EngineeringContext:
    """証拠から Engineering Context を組み立てる（決定論的）。"""
    unobserved = [e for e in evidence if e.scanned_files == 0]
    mismatches = [e for e in evidence if not e.expectation_met]
    claims_without_support = [
        e for e in evidence if claimed_flags.get(e.assumption_id) and e.expectation_met
    ]

    reasons: list[str] = []
    if guard_findings:
        reasons.append(f"検査を弱める変更を {len(guard_findings)} 件検出")
    if mismatches:
        reasons.append(
            "前提と観測の食い違い: " + "、".join(e.assumption_id for e in mismatches)
        )
    if claims_without_support:
        reasons.append(
            "提案文の主張に裏付けが無い: "
            + "、".join(e.assumption_id for e in claims_without_support)
        )
    if unobserved:
        reasons.append("観測できていない前提: " + "、".join(e.assumption_id for e in unobserved))

    difficulty = "high" if reasons else "low"
    if not reasons:
        reasons.append("すべての前提で観測が資産の期待と一致し、提案文の主張とも矛盾しない")

    return EngineeringContext(
        asset_id=asset_id,
        assumption_count=len(evidence),
        unobserved_count=len(unobserved),
        expectation_mismatch_count=len(mismatches),
        unsupported_claim_count=len(claims_without_support),
        guard_finding_count=len(guard_findings),
        difficulty=difficulty,
        reasons=reasons,
    )


def select_model(ctx: EngineeringContext, model_low: str, model_high: str) -> str:
    """難度からモデルを選ぶ。"""
    return model_high if ctx.difficulty == "high" else model_low


def to_headers(ctx: EngineeringContext) -> dict[str, str]:
    """OrcaRouter の Routing DSL が条件として使えるようヘッダー化する。

    こちらでモデルを明示指定しているため、この経路は現時点では冗長である。
    ルーティング側だけで切り替える構成へ移せるかを確かめるために送っている。
    """
    return {
        "X-Engineering-Asset-Id": ctx.asset_id,
        "X-Engineering-Difficulty": ctx.difficulty,
        "X-Engineering-Assumptions": str(ctx.assumption_count),
        "X-Engineering-Mismatches": str(ctx.expectation_mismatch_count),
        "X-Engineering-Unsupported-Claims": str(ctx.unsupported_claim_count),
        "X-Engineering-Guard-Findings": str(ctx.guard_finding_count),
    }
