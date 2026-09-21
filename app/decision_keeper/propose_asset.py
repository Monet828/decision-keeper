"""判定結果から、新しい判断資産の候補を生成する（資産化のループ）。

人の承認なしに判断資産を更新しない、という停止条件を生成側でも守る。
- 既存の資産ファイルは書き換えない。別ディレクトリに新規ファイルとして出す
- 生成物は status: candidate、approved_by: unapproved で固定する
- review は既定で candidate を読み込まない（--include-candidates で明示的に許可）

生成される前提の verify は、実際に観測できた証拠から機械的に組み立てる。
観測から作れない前提は書かない。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .models import DecisionAsset, ReviewResult

CANDIDATE_STATUS = "candidate"
UNAPPROVED = "unapproved"


def _next_id(out_dir: Path, prefix: str = "DP-C") -> str:
    existing = sorted(out_dir.glob(f"{prefix}*.yaml")) if out_dir.is_dir() else []
    return f"{prefix}{len(existing) + 1:03d}"


def build(
    result: ReviewResult,
    source_asset: DecisionAsset,
    proposal_text: str,
    out_dir: Path,
) -> dict:
    """候補資産の中身を組み立てる。ファイルには書かない。"""
    disputed = [j.assumption_id for j in result.judgements if j.status == "disputed"]
    insufficient = [j.assumption_id for j in result.judgements if j.status == "insufficient"]

    # 観測できた証拠だけから前提を作る。作れないものは書かない。
    assumptions = []
    for e in result.assumption_evidence:
        if e.scanned_files == 0:
            continue
        observed_present = len(e.evidence) > 0
        assumptions.append(
            {
                "id": e.assumption_id,
                # 現在の観測を、そのまま新しい前提の記述にする
                "statement": (
                    f"{e.statement}（{result.asset_id} v{result.asset_version} 時点の記述）"
                    if observed_present == (e.expect == "present")
                    else f"[要記述] {e.statement} は現在の観測と食い違っている"
                ),
                "verify": {
                    "method": "grep",
                    "pattern": "[要記述]",
                    "paths": ["[要記述]"],
                    "expect": "present" if observed_present else "absent",
                },
                "_observed": {
                    "scanned_files": e.scanned_files,
                    "evidence_count": len(e.evidence),
                    "paths": sorted({ev.path for ev in e.evidence})[:5],
                },
            }
        )

    if result.verdict == "propose_update":
        problem = f"{source_asset.problem}（{'、'.join(disputed)} の前提が変化した）"
        chosen = "[要記述] 前提が変化したため、判断を見直す必要がある"
        rationale = (
            f"{source_asset.id} v{source_asset.version} の前提 {'、'.join(disputed)} と"
            "現在の観測が食い違うことを確認した。旧判断の理由は次のとおり: "
            f"{source_asset.rationale}"
        )
    else:
        problem = f"{source_asset.problem}（{'、'.join(insufficient)} の根拠が不足）"
        chosen = "[要記述] 判断に必要な証拠が不足している"
        rationale = "観測から判断できなかった。追加で確認すべき点は open_questions を参照。"

    return {
        "id": _next_id(out_dir),
        "version": 1,
        "status": CANDIDATE_STATUS,
        "approved_by": UNAPPROVED,
        "decided_at": date.today().isoformat(),
        "problem": problem,
        "chosen_decision": chosen,
        "rationale": rationale,
        "alternatives": [],
        "constraints": list(source_asset.constraints),
        "assumptions": assumptions,
        "review_triggers": ["人が内容を確認し、[要記述] を埋めるまで利用しない"],
        "applies_to": {
            "paths": list(source_asset.applies_to.paths),
            "keywords": list(source_asset.applies_to.keywords),
        },
        "sources": [
            {"type": "review", "url": f"derived-from:{source_asset.id}#v{source_asset.version}"}
        ],
        "_provenance": {
            "derived_from": source_asset.id,
            "derived_from_version": source_asset.version,
            "verdict": result.verdict,
            "disputed": disputed,
            "insufficient": insufficient,
            "open_questions": result.open_questions,
            "note": (
                "この候補は自動生成であり、承認されていない。"
                "[要記述] を人が埋め、status を established、approved_by を実名に"
                "変えるまで review の入力にしない。"
            ),
        },
    }


def write(candidate: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{candidate['id']}.yaml"
    header = (
        "# 自動生成された判断資産の候補。未承認。\n"
        "# [要記述] を人が埋め、status を established、approved_by を実名に変えるまで\n"
        "# review の入力にしない（--include-candidates を付けない限り読み込まれない）。\n"
    )
    path.write_text(
        header + yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path
