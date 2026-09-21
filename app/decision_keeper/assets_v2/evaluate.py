"""ConditionEvaluation と AssetEvaluation（原典§8, §9）。

Observation（Evidence）から Interpretation（judgment）を作る層。
両者を混ぜないため、Evidence は引数として受け取るだけで書き換えない。

判定は決定論的に行う。LLMには委ねない。
「探索して0件」と「探索していない」をここで分ける（EA-06）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from .schema import (
    AssetEvaluation,
    Condition,
    ConditionEvaluation,
    DecisionAsset,
    Evidence,
    Judgment,
    Verdict,
)

EVALUATOR = "decision-keeper/assets_v2"


def evaluate_condition(
    condition: Condition, evidence: Evidence, claimed_in_task: bool = False
) -> ConditionEvaluation:
    """1つの Condition を評価する（原典§8）。

    claimed_in_task: 今回のタスク説明が、この Condition に関わる変化を主張しているか。
    主張はあるが観測が裏付けない場合、supported にも contradicted にもしない（原典§12, EA-07）。
    """
    judgment, reason = _judge(condition, evidence, claimed_in_task)
    return ConditionEvaluation(
        condition_id=condition.id,
        statement=condition.statement,
        evidence=[evidence.id],
        judgment=judgment,
        reason=reason,
        evaluated_at=datetime.now(timezone.utc),
        evaluator=EVALUATOR,
    )


def _judge(
    condition: Condition, evidence: Evidence, claimed_in_task: bool
) -> tuple[Judgment, str]:
    # 観測できていない。0件とは別物（EA-06）
    if evidence.type == "not_observed":
        why = evidence.observation.get("reason", "観測できなかった")
        return "not_observed", f"観測できていない。{why}"

    obs = evidence.observation
    if evidence.type == "test_result":
        present = bool(obs.get("passed"))
        detail = f"テストの終了コードは {obs.get('exit_code')}"
    else:
        scanned = int(obs.get("files_scanned", 0))
        matches = int(obs.get("matches", 0))
        if scanned == 0:
            return "not_observed", "走査対象が0件だったため観測できていない"
        present = matches > 0
        detail = f"{scanned} ファイルを走査し {matches} 件一致"

    expectation_met = present if condition.expectation == "present" else not present

    # タスクが変化を主張しているのに、観測は以前の期待どおり = 裏付けが無い
    if claimed_in_task and expectation_met:
        return (
            "insufficient",
            f"タスク説明は変化を主張しているが、{detail}であり期待 "
            f"{condition.expectation} のまま。主張を裏付ける観測が無い",
        )

    if expectation_met:
        if condition.expectation == "absent":
            return "supported", f"{detail}。探索した結果として存在しないことを確認した"
        return "supported", f"{detail}。期待 present と観測が一致した"

    return "contradicted", f"{detail}。期待 {condition.expectation} と観測が食い違う"


def decide_verdict(
    evaluations: list[ConditionEvaluation], human_review_required: bool
) -> tuple[Verdict, str]:
    """Asset 全体の verdict を決める（原典§9, §15）。決定論的。"""
    if human_review_required:
        return (
            "hold",
            "自動確認できない Condition（human / document_search）を含むため、"
            "完全自律では適用しない（原典§5, EA-08）",
        )
    if not evaluations:
        return "hold", "評価対象の Condition が無い"

    not_observed = [e for e in evaluations if e.judgment == "not_observed"]
    insufficient = [e for e in evaluations if e.judgment == "insufficient"]
    contradicted = [e for e in evaluations if e.judgment == "contradicted"]

    if not_observed:
        ids = "、".join(e.condition_id for e in not_observed)
        return "hold", f"観測できていない Condition がある（{ids}）"
    if insufficient:
        ids = "、".join(e.condition_id for e in insufficient)
        return "hold", f"根拠が不足する Condition がある（{ids}）。肯定にも否定にも倒さない"
    if contradicted:
        ids = "、".join(e.condition_id for e in contradicted)
        return (
            "propose_update",
            f"Condition の前提が現在の観測と食い違う（{ids}）。"
            "判断の見直しを提案する。Approved Asset は書き換えない（EA-03）",
        )
    return "inherit", "すべての Condition が現在も成立している。過去の判断を継承する"


def evaluate_asset(
    asset: DecisionAsset,
    task_id: str,
    evidence_by_condition: dict[str, Evidence],
    claimed: dict[str, bool] | None = None,
    selection_reason: str = "",
) -> AssetEvaluation:
    """Decision Asset を現在の条件で評価する（原典§9）。"""
    claimed = claimed or {}
    evaluations: list[ConditionEvaluation] = []
    collected: list[Evidence] = []

    for condition in asset.conditions:
        if condition.status != "active":
            continue
        ev = evidence_by_condition.get(condition.id)
        if ev is None:
            continue
        collected.append(ev)
        evaluations.append(
            evaluate_condition(condition, ev, claimed_in_task=claimed.get(condition.id, False))
        )

    needs_human = asset.requires_human_review
    verdict, reason = decide_verdict(evaluations, needs_human)

    return AssetEvaluation(
        asset_id=asset.id,
        asset_version=asset.version,
        task_id=task_id,
        condition_evaluations=evaluations,
        verdict=verdict,
        verdict_reason=reason,
        evidence=collected,
        human_review_required=needs_human,
        selection_reason=selection_reason,
    )
