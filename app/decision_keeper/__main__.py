"""CLI。判断資産と変更提案を受け取り、継承／更新提案／保留を判定する。

処理は単方向で、自律ループを持たない（ignight の propose-fix.ts の型を踏襲）。
  資産選択(決定論) -> 証拠収集(決定論) -> 前提判定(LLM 1回) -> 総合判定(決定論) -> レポート
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .assets import AssetError, load_assets, verify_unchanged
from .collect.collectors import collect_all
from .context import DEFAULT_MODEL_HIGH, DEFAULT_MODEL_LOW, compute, select_model
from .diff_guard import scan_diff
from .judge import _claimed_in_proposal_by_id, judge
from .limits import (
    DEFAULT_MAX_LLM_CALLS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TIMEOUT_SEC,
    Limits,
)
from .llm import build_client
from .models import EXIT_CODES, ReviewResult
from .report import write
from .select import select
from .verdict import decide


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m decision_keeper",
        description="過去の技術判断の前提が現在も成立するかを判定する。",
    )
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("review", help="変更提案をレビューする")
    r.add_argument("--assets", type=Path, required=True, help="判断資産YAMLのディレクトリ")
    r.add_argument(
        "--change", type=Path, required=True,
        help="diff.patch と proposal.md のあるディレクトリ",
    )
    r.add_argument("--repo", type=Path, required=True, help="証拠収集の対象リポジトリ")
    r.add_argument("--out", type=Path, required=True, help="Markdownレポートの出力先")
    r.add_argument("--max-llm-calls", type=int, default=DEFAULT_MAX_LLM_CALLS)
    r.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    r.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    r.add_argument("--stub", action="store_true", help="APIキーがあっても固定応答を使う")
    r.add_argument(
        "--propose-asset",
        type=Path,
        help="判定結果から新しい判断資産の候補を生成する出力先ディレクトリ（未承認で出る）",
    )
    r.add_argument(
        "--include-candidates",
        action="store_true",
        help="未承認の候補資産も読み込む（既定では除外される）",
    )
    r.add_argument("--model-low", default=DEFAULT_MODEL_LOW, help="難度lowで使うモデル")
    r.add_argument("--model-high", default=DEFAULT_MODEL_HIGH, help="難度highで使うモデル")
    ev = sub.add_parser("evaluate", help="Task に対し Engineering Asset を検索・評価する")
    ev.add_argument("--assets", type=Path, required=True, help="Asset ディレクトリ")
    ev.add_argument(
        "--task", type=Path, required=True,
        help="task.md と diff.patch のあるディレクトリ",
    )
    ev.add_argument("--repo", type=Path, required=True, help="Verifier を実行する対象リポジトリ")
    ev.add_argument("--out", type=Path, required=True)
    ev.add_argument("--task-id", default="", help="省略時は --task のディレクトリ名")
    ev.add_argument(
        "--include-candidates", action="store_true",
        help="未承認候補も検索対象にする（既定では除外）",
    )

    c = sub.add_parser("compare", help="判断資産あり/なしを比較する")
    c.add_argument("--assets", type=Path, required=True)
    c.add_argument("--cases", type=Path, required=True, help="事例ディレクトリの親")
    c.add_argument("--case", action="append", required=True, help="事例名（複数指定可）")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    c.add_argument("--stub", action="store_true")
    c.add_argument("--model-low", default=DEFAULT_MODEL_LOW)
    c.add_argument("--model-high", default=DEFAULT_MODEL_HIGH)

    r.add_argument(
        "--no-context-routing",
        action="store_true",
        help="Engineering Contextによるモデル切り替えを止め、既定モデルを使う",
    )
    return p



def _conflicting_changes(asset, diff_text: str) -> list:
    """継承判定のとき、資産が統べるパスに触れた変更を衝突として挙げる（R-04）。"""
    import fnmatch

    from .models import Evidence
    from .select import changed_paths

    out: list[Evidence] = []
    for path in changed_paths(diff_text):
        if any(fnmatch.fnmatch(path, pat) for pat in asset.applies_to.paths):
            for lineno, line in enumerate(diff_text.splitlines(), start=1):
                if line.startswith("+") and not line.startswith("+++") and line[1:].strip():
                    out.append(
                        Evidence(
                            collector="grep",
                            path=path,
                            line=lineno,
                            excerpt=line[1:].strip()[:200],
                        )
                    )
    return out


def run_review(args: argparse.Namespace) -> int:
    diff_path = args.change / "diff.patch"
    proposal_path = args.change / "proposal.md"
    for path in (diff_path, proposal_path):
        if not path.exists():
            print(f"入力が見つかりません: {path}", file=sys.stderr)
            return 2

    diff_text = diff_path.read_text(encoding="utf-8")
    proposal_text = proposal_path.read_text(encoding="utf-8")

    try:
        assets, digests = load_assets(args.assets, include_candidates=args.include_candidates)
    except AssetError as exc:
        print(f"判断資産を読めません: {exc}", file=sys.stderr)
        return 2

    selected = select(assets, diff_text, proposal_text)
    if not selected:
        print("この変更に関連する判断資産は見つかりませんでした。", file=sys.stderr)
        return 2

    asset, selection_reason = selected[0]
    limits = Limits(
        max_llm_calls=args.max_llm_calls,
        max_tokens=args.max_tokens,
        timeout_sec=args.timeout_sec,
    )

    evidence = collect_all(args.repo, asset.assumptions)
    guard_findings = scan_diff(diff_text)

    # Engineering Context は決定論的な観測だけから決まる（LLM呼び出しより前）
    claimed = {
        a.id: _claimed_in_proposal_by_id(asset, a.id, proposal_text) for a in asset.assumptions
    }
    ctx = compute(asset.id, evidence, guard_findings, claimed)
    if not args.no_context_routing:
        ctx.selected_model = select_model(ctx, args.model_low, args.model_high)

    client = build_client(force_stub=args.stub, timeout_sec=float(args.timeout_sec))
    judgements, cost = judge(
        client, asset, evidence, diff_text, proposal_text, limits, ctx=ctx
    )
    verdict, verdict_reason = decide(judgements, guard_findings)

    conflicts = (
        _conflicting_changes(asset, diff_text) if verdict == "inherit" else []
    )
    open_questions = [
        f"{j.assumption_id}「"
        f"{next(e.statement for e in evidence if e.assumption_id == j.assumption_id)}」"
        f" を確認する証拠。{j.reason}"
        for j in judgements
        if j.status == "insufficient"
    ]

    unchanged, changed = verify_unchanged(digests)
    if not unchanged:
        print(f"判断資産が実行中に変更されました: {changed}", file=sys.stderr)

    result = ReviewResult(
        asset_id=asset.id,
        asset_version=asset.version,
        verdict=verdict,
        verdict_reason=verdict_reason,
        selection_reason=selection_reason,
        assumption_evidence=evidence,
        judgements=judgements,
        guard_findings=guard_findings,
        conflicts=conflicts,
        open_questions=open_questions,
        costs=[cost] if cost else [],
        limits_hit=limits.hits,
        assets_unchanged=unchanged,
        engineering_context=ctx,
    )

    if args.propose_asset and verdict in ("propose_update", "hold"):
        from .propose_asset import build
        from .propose_asset import write as write_candidate

        candidate = build(result, asset, proposal_text, args.propose_asset)
        cand_path = write_candidate(candidate, args.propose_asset)
        print(f"候補資産: {cand_path} (未承認。人が確認するまで review では読まれない)")

    json_path = write(result, args.out)
    print(f"難度: {ctx.difficulty}  モデル: {ctx.selected_model or '(既定)'}")
    print(f"判定: {verdict}")
    print(f"レポート: {args.out}")
    print(f"JSON:     {json_path}")

    if not unchanged:
        return 3
    return EXIT_CODES[verdict]


def run_compare(args: argparse.Namespace) -> int:
    from .compare import run_comparison, to_markdown

    client = build_client(force_stub=args.stub, timeout_sec=float(args.timeout_sec))
    report = run_comparison(
        client,
        args.assets,
        args.cases,
        args.case,
        args.timeout_sec,
        args.model_low,
        args.model_high,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(to_markdown(report), encoding="utf-8")
    args.out.with_suffix(".json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"比較結果: {args.out}")
    for c in report.cases:
        w, wo = c.with_asset, c.without_asset
        print(
            f"  {c.case}: 資産あり {w.verdict}({w.prompt_tokens + w.completion_tokens}tok) "
            f"/ 資産なし {wo.verdict}({wo.prompt_tokens + wo.completion_tokens}tok)"
        )
    return 0


def run_evaluate(args: argparse.Namespace) -> int:
    from .assets_v2.agent import Task
    from .assets_v2.agent import run as run_agent
    from .assets_v2.report import write as write_report
    from .assets_v2.store import AssetStore, StoreError

    task_md = args.task / "task.md"
    diff = args.task / "diff.patch"
    if not task_md.exists():
        print(f"task.md が見つかりません: {task_md}", file=sys.stderr)
        return 2

    try:
        store = AssetStore.load(args.assets, include_candidates=args.include_candidates)
    except StoreError as exc:
        print(f"Asset を読めません: {exc}", file=sys.stderr)
        return 2

    task = Task(
        id=args.task_id or args.task.name,
        description=task_md.read_text(encoding="utf-8"),
        diff=diff.read_text(encoding="utf-8") if diff.exists() else "",
    )
    result = run_agent(store, task, args.repo)
    json_path = write_report(result, args.out)

    e = result.evaluation
    print(f"判定: {e.verdict if e else '(該当Assetなし)'}")
    print(f"人の確認が必要: {result.engineering_context.human_review_required}")
    print(f"再利用可: {result.reusable_implementations or 'なし'}")
    print(f"レポート: {args.out}")
    print(f"JSON:     {json_path}")
    for n in result.notes:
        print(f"  - {n}")
    if not result.assets_unchanged:
        return 3
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "review":
        return run_review(args)
    if args.command == "evaluate":
        return run_evaluate(args)
    if args.command == "compare":
        return run_compare(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
