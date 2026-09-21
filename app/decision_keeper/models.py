"""判断資産と証拠のデータモデル。

FACTS（決定論的に観測した証拠）と INTERPRETATION（LLMの判定）を型として分ける。
folder-lens の decisionEpisodes スキーマの語彙を踏襲している。
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

VerifyMethod = Literal["grep", "file_exists", "ast_test_shape", "run_tests"]
AssumptionStatus = Literal["supported", "disputed", "insufficient"]
Verdict = Literal["inherit", "propose_update", "hold"]

# 判定と終了コードの対応（mvp-v0.2-design.md §2）
EXIT_CODES: dict[str, int] = {"inherit": 0, "propose_update": 10, "hold": 20}


# --- 判断資産（入力、読み取り専用） ---


class Verify(BaseModel):
    """前提を検証する決定論的コレクタへの指示。LLMは関与しない。"""

    method: VerifyMethod
    pattern: str | None = None
    paths: list[str] = Field(default_factory=list)
    expect: Literal["present", "absent"] = "present"


class Assumption(BaseModel):
    """判断が成り立つ条件。AI HACK側で追加した第一級フィールド。"""

    id: str
    statement: str
    verify: Verify


class Alternative(BaseModel):
    option: str
    rejected_because: str


class AppliesTo(BaseModel):
    paths: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class Source(BaseModel):
    type: str
    url: str | None = None


class DecisionAsset(BaseModel):
    """1つの技術判断。1 YAMLファイル = 1判断。"""

    id: str
    version: int
    status: Literal["draft", "candidate", "established"]
    approved_by: str
    decided_at: date
    problem: str
    chosen_decision: str
    rationale: str
    alternatives: list[Alternative] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[Assumption]
    review_triggers: list[str] = Field(default_factory=list)
    applies_to: AppliesTo
    sources: list[Source] = Field(default_factory=list)


# --- FACTS: 決定論的に観測した証拠 ---


class Evidence(BaseModel):
    """観測事実。LLMの解釈を含めない。"""

    collector: VerifyMethod
    path: str
    line: int | None = None
    excerpt: str = ""


class AssumptionEvidence(BaseModel):
    """1つの前提に対する収集結果。

    expectation_met は「資産が書いた expect と観測が一致したか」であり、
    前提が成立するかの判定ではない。判定は LLM が行い status に入る。
    """

    assumption_id: str
    statement: str
    expect: Literal["present", "absent"]
    scanned_files: int
    evidence: list[Evidence] = Field(default_factory=list)
    expectation_met: bool
    collector_note: str = ""


# --- INTERPRETATION: LLMの判定 ---


class AssumptionJudgement(BaseModel):
    assumption_id: str
    status: AssumptionStatus
    reason: str


class JudgementSet(BaseModel):
    """LLM出力のスキーマ。検証に失敗したら全件 insufficient に落とす。"""

    judgements: list[AssumptionJudgement]


# --- ガード検出（R-10） ---


class GuardFinding(BaseModel):
    kind: Literal["test_skipped", "test_only", "test_deleted", "assertion_removed"]
    path: str
    line: int | None = None
    excerpt: str = ""


# --- Engineering Context（証拠から決まる難度。OrcaRouterへ渡す） ---


class EngineeringContext(BaseModel):
    """判定前に、決定論的な観測だけから決まる難度。LLMは関与しない。"""

    asset_id: str
    assumption_count: int
    unobserved_count: int
    expectation_mismatch_count: int
    unsupported_claim_count: int
    guard_finding_count: int
    difficulty: Literal["low", "high"]
    reasons: list[str] = Field(default_factory=list)
    selected_model: str = ""


# --- 費用記録（R-07） ---


class CostRecord(BaseModel):
    stage: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float | None = None
    elapsed_sec: float = 0.0
    is_stub: bool = False


# --- 最終出力 ---


class ReviewResult(BaseModel):
    asset_id: str
    asset_version: int
    verdict: Verdict
    verdict_reason: str
    selection_reason: str
    assumption_evidence: list[AssumptionEvidence]
    judgements: list[AssumptionJudgement]
    guard_findings: list[GuardFinding] = Field(default_factory=list)
    conflicts: list[Evidence] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    costs: list[CostRecord] = Field(default_factory=list)
    limits_hit: list[str] = Field(default_factory=list)
    assets_unchanged: bool = True
    engineering_context: EngineeringContext | None = None
