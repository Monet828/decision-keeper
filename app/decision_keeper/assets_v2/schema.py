"""Engineering Asset のデータモデル（要件定義 v0.1）。

原典 §7 の原則をここで型として担保する。
- Observation（Evidence）と Interpretation（ConditionEvaluation）を別の型にする
- Evidence に judgment 相当のフィールドを持たせない（EA-04）
- 「探索して0件」と「探索していない」を別の judgment にする（EA-06）
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# --- 語彙（原典§8, §9, §11, §13, §14） ---

AssetType = Literal["decision", "implementation"]
AssetStatus = Literal["candidate", "approved", "deprecated", "superseded"]
Expectation = Literal["present", "absent"]
Judgment = Literal["supported", "contradicted", "insufficient", "not_observed"]
Verdict = Literal["inherit", "propose_update", "hold"]

VerifierType = Literal[
    "grep", "file_exists", "config_value", "dependency_version",
    "test", "document_search", "human",
]
# 自動では確認できない verifier（原典§5）。これを含むと human_review_required。
MANUAL_VERIFIERS: set[str] = {"human", "document_search"}

ProvenanceType = Literal[
    "orca_run", "pull_request", "commit", "issue", "adr",
    "test_result", "benchmark", "document", "human_input",
]
Relationship = Literal[
    "implements", "implemented_by", "supersedes", "superseded_by", "relates_to",
]

EXIT_CODES: dict[str, int] = {"inherit": 0, "propose_update": 10, "hold": 20}


# --- 共通（原典§13, §14） ---


class Provenance(BaseModel):
    type: ProvenanceType
    ref: str
    note: str = ""


class AssetRelation(BaseModel):
    id: str
    relationship: Relationship


class Rationale(BaseModel):
    """理由。trace から取れない場合は unknown のまま残す（原典§12, EA-07）。"""

    status: Literal["known", "unknown", "needs_review"] = "unknown"
    text: str = ""

    @model_validator(mode="after")
    def _known_needs_text(self):
        if self.status == "known" and not self.text.strip():
            raise ValueError("rationale.status=known には text が必要")
        return self


# --- Condition（原典§4） ---


class Verifier(BaseModel):
    type: VerifierType
    targets: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    note: str = ""

    @property
    def is_manual(self) -> bool:
        return self.type in MANUAL_VERIFIERS


class Condition(BaseModel):
    id: str
    statement: str
    expectation: Expectation = "present"
    verifier: Verifier
    source: str = ""
    status: Literal["active", "retired"] = "active"


# --- Evidence（原典§6）。判断を含めてはならない（EA-04） ---


class Evidence(BaseModel):
    id: str
    type: Literal[
        "grep_result", "file_list", "test_result", "config_value",
        "dependency_version", "document_hit", "human_input", "not_observed",
    ]
    observation: dict = Field(default_factory=dict)
    query: dict = Field(default_factory=dict)
    source: dict = Field(default_factory=dict)
    samples: list[dict] = Field(default_factory=list)


# --- Asset 本体（原典§2） ---


class AppliesTo(BaseModel):
    paths: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class Alternative(BaseModel):
    option: str
    rejected_because: str = ""


class AssetBase(BaseModel):
    id: str
    type: AssetType
    version: int = 1
    status: AssetStatus = "candidate"
    approved_by: str = ""
    decided_at: date | None = None
    supersedes: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    related_assets: list[AssetRelation] = Field(default_factory=list)
    applies_to: AppliesTo = Field(default_factory=AppliesTo)

    @model_validator(mode="after")
    def _approved_needs_provenance(self):
        """provenance の無い Asset は approved にできない（EA-10）。"""
        if self.status == "approved" and not self.provenance:
            raise ValueError(f"{self.id}: approved には provenance が必要（EA-10）")
        if self.status == "approved" and not self.approved_by.strip():
            raise ValueError(f"{self.id}: approved には approved_by が必要")
        return self


class DecisionAsset(AssetBase):
    """WHY / WHEN — なぜそう判断し、どの条件で適用するか（原典§2.2）。"""

    type: Literal["decision"] = "decision"
    question: str
    decision: str
    rationale: Rationale = Field(default_factory=Rationale)
    conditions: list[Condition] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)

    @property
    def requires_human_review(self) -> bool:
        """自動確認できない Condition を含むか（原典§5, EA-08）。"""
        return any(c.verifier.is_manual for c in self.conditions if c.status == "active")


class ImplementationAsset(AssetBase):
    """HOW — どう実装したか（原典§2.1）。

    「このコードが存在する」ではなく
    「この目的を満たす実装が、この条件下で、この検証を通過した」という主張。
    """

    type: Literal["implementation"] = "implementation"
    purpose: str
    implementation: dict = Field(default_factory=dict)   # repository, commit, paths, entrypoint
    compatibility: dict = Field(default_factory=dict)    # runtime, dependencies, requires
    verification: dict = Field(default_factory=dict)     # tests


# --- 評価（原典§8, §9）。Asset とは別オブジェクトにする ---


class ConditionEvaluation(BaseModel):
    condition_id: str
    statement: str = ""
    evidence: list[str] = Field(default_factory=list)
    judgment: Judgment
    reason: str = ""
    evaluated_at: datetime | None = None
    evaluator: str = ""


class AssetEvaluation(BaseModel):
    asset_id: str
    asset_version: int
    task_id: str
    condition_evaluations: list[ConditionEvaluation] = Field(default_factory=list)
    verdict: Verdict
    verdict_reason: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    human_review_required: bool = False
    selection_reason: str = ""

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.verdict]
