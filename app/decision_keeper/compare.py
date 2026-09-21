"""判断資産あり/なしの比較実験（Reasoning Amortization の検証）。

同じ事例を両方式で流し、トークン・呼び出し回数・所要時間・
「過去の設計判断との衝突を検出できたか」を並べる。

測れるのは1回の推論コストの比較であり、エージェント全体の総コストではない。
資産側は決定論的な証拠収集を行うが、そこにLLMは関与しないため
モデル呼び出し回数には現れない。この非対称性はレポートに明記する。
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from . import baseline
from .assets import load_assets
from .collect.collectors import collect_all
from .context import compute, select_model
from .diff_guard import scan_diff
from .judge import _claimed_in_proposal_by_id, judge
from .limits import Limits
from .llm import LLMClient
from .models import EXIT_CODES
from .select import select
from .verdict import decide

# 資産あり側で「衝突を検出した」とみなす判定
CONFLICT_VERDICTS = {"inherit", "propose_update", "hold"}


class Arm(BaseModel):
    name: str
    verdict: str = ""
    detected_conflict: bool = False
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_sec: float = 0.0
    model: str = ""
    note: str = ""


class CaseComparison(BaseModel):
    case: str
    with_asset: Arm
    without_asset: Arm


class ComparisonReport(BaseModel):
    cases: list[CaseComparison] = Field(default_factory=list)


def _run_with_asset(
    client: LLMClient, assets_dir: Path, case_dir: Path, repo: Path, timeout: int
) -> Arm:
    diff = (case_dir / "diff.patch").read_text(encoding="utf-8")
    proposal = (case_dir / "proposal.md").read_text(encoding="utf-8")
    assets, _ = load_assets(assets_dir)
    selected = select(assets, diff, proposal)
    if not selected:
        return Arm(name="判断資産あり", note="関連する資産が見つからなかった")

    asset, _ = selected[0]
    limits = Limits(timeout_sec=timeout)
    evidence = collect_all(repo, asset.assumptions)
    guard = scan_diff(diff)
    claimed = {a.id: _claimed_in_proposal_by_id(asset, a.id, proposal) for a in asset.assumptions}
    ctx = compute(asset.id, evidence, guard, claimed)
    ctx.selected_model = select_model(ctx, *_MODELS)

    judgements, cost = judge(client, asset, evidence, diff, proposal, limits, ctx=ctx)
    verdict, _ = decide(judgements, guard)

    # 継承は「衝突する変更箇所を指摘した」状態、更新提案と保留も論点を示している
    detected = verdict in CONFLICT_VERDICTS and EXIT_CODES[verdict] is not None
    return Arm(
        name="判断資産あり",
        verdict=verdict,
        detected_conflict=detected,
        llm_calls=limits.llm_calls_used,
        prompt_tokens=cost.prompt_tokens if cost else 0,
        completion_tokens=cost.completion_tokens if cost else 0,
        elapsed_sec=cost.elapsed_sec if cost else 0.0,
        model=cost.model if cost else "",
        note=f"難度 {ctx.difficulty}",
    )


def _run_without_asset(client: LLMClient, case_dir: Path, repo: Path, timeout: int) -> Arm:
    diff = (case_dir / "diff.patch").read_text(encoding="utf-8")
    proposal = (case_dir / "proposal.md").read_text(encoding="utf-8")
    limits = Limits(timeout_sec=timeout)
    res = baseline.run(client, repo, diff, proposal, limits, model=_MODELS[1])
    c = res.cost
    return Arm(
        name="判断資産なし",
        verdict=res.verdict,
        detected_conflict=res.detected_conflict,
        llm_calls=limits.llm_calls_used,
        prompt_tokens=c.prompt_tokens if c else 0,
        completion_tokens=c.completion_tokens if c else 0,
        elapsed_sec=c.elapsed_sec if c else 0.0,
        model=c.model if c else "",
        note=res.reason[:80],
    )


_MODELS: tuple[str, str] = ("", "")


def run_comparison(
    client: LLMClient,
    assets_dir: Path,
    cases_dir: Path,
    case_names: list[str],
    timeout: int,
    model_low: str,
    model_high: str,
) -> ComparisonReport:
    global _MODELS
    _MODELS = (model_low, model_high)

    report = ComparisonReport()
    for name in case_names:
        case_dir = cases_dir / name
        repo = case_dir / "repo"
        report.cases.append(
            CaseComparison(
                case=name,
                with_asset=_run_with_asset(client, assets_dir, case_dir, repo, timeout),
                without_asset=_run_without_asset(client, case_dir, repo, timeout),
            )
        )
    return report


def to_markdown(r: ComparisonReport) -> str:
    lines: list[str] = []
    a = lines.append
    a("# 判断資産あり / なし の比較")
    a("")
    a("同じ変更提案・同じリポジトリを与え、判断資産の有無だけを変えている。")
    a("")
    a(
        "| 事例 | 方式 | 判定 | 論点を示せたか | 呼び出し | 入力tok | 出力tok "
        "| 合計tok | 所要 | モデル |"
    )
    a("|---|---|---|---|---|---|---|---|---|---|")
    for c in r.cases:
        for arm in (c.with_asset, c.without_asset):
            total = arm.prompt_tokens + arm.completion_tokens
            mark = "はい" if arm.detected_conflict else "いいえ"
            a(
                f"| {c.case} | {arm.name} | {arm.verdict or '-'} | {mark} | {arm.llm_calls} | "
                f"{arm.prompt_tokens} | {arm.completion_tokens} | {total} | "
                f"{arm.elapsed_sec:.1f}s | `{arm.model}` |"
            )
    a("")

    w = sum(c.with_asset.prompt_tokens + c.with_asset.completion_tokens for c in r.cases)
    wo = sum(c.without_asset.prompt_tokens + c.without_asset.completion_tokens for c in r.cases)
    a(f"- 判断資産あり 合計トークン: **{w}**")
    a(f"- 判断資産なし 合計トークン: **{wo}**")
    a(
        f"- 差: {w - wo:+d} ({(w / wo - 1) * 100:+.1f}%)"
        if wo
        else "- 差: 算出不能"
    )
    a("")
    a("## この比較で測れていないこと")
    a("")
    a("- 資産なし側は**LLMに1回尋ねるだけ**で、通常のコーディングエージェントのような")
    a("  ツール反復・ファイル探索を行っていない。実際のエージェントはより多く消費する。")
    a("- 資産あり側の決定論的な証拠収集はLLMを使わないため、モデル呼び出し回数に現れない。")
    a("  計算資源は消費しているが、ここでは計上していない。")
    a("- 判断資産を人間が書くコストは計上していない。")
    a("- **したがって本表は、単発レビューという条件での結果にすぎない。**")
    a("  実装資産の再利用や、開発完了までの複数工程は測っていない。")
    a("  言えるのは、同じ問いに1回答えさせたときの入出力トークンと、")
    a("  論点を示せたかの違いだけである。")
    a("")
    return "\n".join(lines)
