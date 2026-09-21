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
from .diff_guard import scan_diff
from .judge import judge
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
        assets, digests = load_assets(args.assets)
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
    client = build_client(force_stub=args.stub)
    judgements, cost = judge(client, asset, evidence, diff_text, proposal_text, limits)
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
    )

    json_path = write(result, args.out)
    print(f"判定: {verdict}")
    print(f"レポート: {args.out}")
    print(f"JSON:     {json_path}")

    if not unchanged:
        return 3
    return EXIT_CODES[verdict]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "review":
        return run_review(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
