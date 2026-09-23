"""Execution Agent の検索・評価経路（原典§15）。

Task -> Asset Retrieval -> Condition確認 -> Verifier実行 -> Evidence生成
     -> ConditionEvaluation -> AssetEvaluation -> verdict

今回の範囲は評価まで。実装資産の適用とテスト実行は行わない（§18, ユーザー選択）。
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from . import context as ctx_mod
from . import verifiers
from .evaluate import evaluate_asset
from .schema import AssetEvaluation, DecisionAsset, ImplementationAsset
from .. import scope
from .store import AssetStore

DIFF_PATH = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


class Task(BaseModel):
    """開発タスク。差分があれば渡すが、無くても検索はできる。"""

    id: str
    description: str = ""
    diff: str = ""

    @property
    def changed_paths(self) -> list[str]:
        return sorted({p.strip() for p in DIFF_PATH.findall(self.diff) if p.strip() != "/dev/null"})

    @property
    def text(self) -> str:
        return f"{self.description}\n{self.diff}"


# 保守的な順。複数 Asset に当たったとき、最も強い側を全体の verdict にする。
VERDICT_PRIORITY = {"hold": 3, "propose_update": 2, "inherit": 1}


class AgentResult(BaseModel):
    task_id: str
    evaluations: list[AssetEvaluation] = Field(default_factory=list)
    evaluation: AssetEvaluation | None = None  # 全体を代表する1件（最も保守的なもの）
    engineering_context: ctx_mod.EngineeringContext
    reusable_implementations: list[str] = Field(default_factory=list)
    blocked_implementations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    assets_unchanged: bool = True

    @property
    def exit_code(self) -> int:
        return self.evaluation.exit_code if self.evaluation else 20


def _claims(asset: DecisionAsset, task: Task) -> dict[str, bool]:
    """タスク説明が、その Condition に関わる変化を主張しているか（決定論的）。"""
    low = task.description.lower()
    out: dict[str, bool] = {}
    for c in asset.conditions:
        words = [w for w in c.verifier.patterns if len(w) > 2]
        out[c.id] = any(w.lower() in low for w in words)
    return out


def run(store: AssetStore, task: Task, repo: Path) -> AgentResult:
    """Task に対し Asset を検索して評価する（原典§15）。"""
    # EA-13: 差分が無いとき(着手時・検証専用の run)は、適用範囲の実在で照合する。
    changed = task.changed_paths
    rpaths = scope.repo_paths(repo) if not changed else None
    decisions = store.search_decisions(changed, task.text, rpaths)
    notes: list[str] = []
    if store.skipped:
        notes.append("未承認のため検索対象から除外: " + "、".join(store.skipped))

    if not decisions:
        unchanged, changed = store.verify_unchanged()
        return AgentResult(
            task_id=task.id,
            engineering_context=ctx_mod.build(None),
            notes=notes + ["関連する Decision Asset が見つからなかった"],
            assets_unchanged=unchanged,
        )

    # 該当した Asset をすべて評価する。1件だけ見ると、広い Asset が他を覆い隠す。
    evaluations: list[AssetEvaluation] = []
    for asset, selection_reason in decisions:
        evidence_by_condition = {
            c.id: verifiers.run(repo, c) for c in asset.conditions if c.status == "active"
        }
        evaluations.append(
            evaluate_asset(
                asset, task.id, evidence_by_condition, _claims(asset, task), selection_reason
            )
        )

    # 全体の verdict は最も保守的なものを採る
    evaluations.sort(key=lambda e: VERDICT_PRIORITY[e.verdict], reverse=True)
    evaluation = evaluations[0]
    if len(evaluations) > 1:
        notes.append(
            "評価した Asset: "
            + "、".join(f"{e.asset_id}={e.verdict}" for e in evaluations)
            + f" → 全体は最も保守的な {evaluation.verdict}"
        )

    engineering_context = ctx_mod.build(evaluation)
    # 1件でも人の確認が必要なら全体として必要
    engineering_context.human_review_required = any(
        e.human_review_required for e in evaluations
    )

    # 紐づく Implementation Asset の再利用可否（原典§14）
    # 関連するすべての判断が inherit で、かつ全体として人の確認が不要なときだけ
    # 再利用可とする。人の確認が要る場面で自律的に適用しない（原典§5, EA-08）。
    needs_human = engineering_context.human_review_required
    reusable: list[str] = []
    blocked: list[str] = []
    for impl in store.implementations.values():
        related_ids = {r.id for r in impl.related_assets}
        relevant = [
            e for e in evaluations
            if e.asset_id in related_ids
            or impl.id in {r.id for r in store.decisions[e.asset_id].related_assets}
        ]
        if not relevant:
            continue
        if needs_human:
            blocked.append(impl.id)
            notes.append(
                f"実装資産 {impl.id} は再利用対象にしない。"
                "自動確認できない Condition があり、人の確認が必要（EA-08）"
            )
        elif all(e.verdict == "inherit" for e in relevant):
            reusable.append(impl.id)
        else:
            blocked.append(impl.id)
            notes.append(
                f"実装資産 {impl.id} は再利用対象にしない。判断ゲート: "
                + "、".join(f"{e.asset_id}={e.verdict}" for e in relevant)
            )

    unchanged, changed = store.verify_unchanged()
    if not unchanged:
        notes.append(f"Approved Asset が実行中に変更された: {changed}")

    return AgentResult(
        task_id=task.id,
        evaluations=evaluations,
        evaluation=evaluation,
        engineering_context=engineering_context,
        reusable_implementations=reusable,
        blocked_implementations=blocked,
        notes=notes,
        assets_unchanged=unchanged,
    )


def describe_implementation(impl: ImplementationAsset) -> str:
    """再利用候補の要約。実際の適用は今回の範囲外。"""
    paths = "、".join(impl.implementation.get("paths", []))
    tests = "、".join(t.get("command", "") for t in impl.verification.get("tests", []))
    return f"{impl.id} v{impl.version}: {impl.purpose} / 実装 {paths} / 検証 {tests}"
