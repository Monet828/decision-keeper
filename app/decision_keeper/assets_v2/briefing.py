"""Execution Agent が LLM へ手渡す資料を組み立てる（案A の実行段）。

責務の分担:
- Agent : どの資産を渡すか（Retrieval + Condition 再検証）、実装資産の中身を読むこと、
          verification.tests を実際に走らせること
- LLM   : コードを書くこと、移植元の特定、設計判断

Agent は資産を「渡す」だけで、内容を書き換えない。
Approved Asset は読み取り専用（EA-03）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from .agent import AgentResult
from .schema import ImplementationAsset
from .store import AssetStore

MAX_SNIPPET_LINES = 120


class SourceSnippet(BaseModel):
    path: str
    found: bool
    lines: int = 0
    text: str = ""
    note: str = ""


class Briefing(BaseModel):
    """LLM へ渡す資料。ここに無いものは LLM が自分で探すことになる。"""

    task_id: str
    verdict: str = ""
    decisions: list[dict] = Field(default_factory=list)
    implementations: list[dict] = Field(default_factory=list)
    snippets: list[SourceSnippet] = Field(default_factory=list)
    verify_commands: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    withheld: list[str] = Field(default_factory=list)


def _read_entrypoint(repo: Path, impl: ImplementationAsset) -> list[SourceSnippet]:
    """実装資産が指すコードを実際に読む。

    entrypoint が `path:symbol` 形式なら、その symbol の定義位置から抜き出す。
    見つからなければ found=False として残す（存在するふりをしない）。
    """
    out: list[SourceSnippet] = []
    entry = str(impl.implementation.get("entrypoint", ""))
    symbol = entry.split(":", 1)[1] if ":" in entry else ""

    for rel in impl.implementation.get("paths", []):
        path = repo / rel
        if not path.exists():
            out.append(SourceSnippet(path=rel, found=False, note="実装資産が指すパスが存在しない"))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        start = 0
        note = "ファイル先頭から"
        if symbol:
            for i, line in enumerate(lines):
                if symbol in line and ("function" in line or "export" in line or "const" in line):
                    start = max(0, i - 25)  # 直前のコメント（判断の記録）も一緒に渡す
                    note = f"{symbol} の定義付近（{start + 1} 行目から）"
                    break
        chunk = lines[start : start + MAX_SNIPPET_LINES]
        out.append(
            SourceSnippet(
                path=rel, found=True, lines=len(lines),
                text="\n".join(chunk), note=note,
            )
        )
    return out


def build(store: AssetStore, result: AgentResult, repo: Path) -> Briefing:
    """評価結果から、LLM への手渡し資料を作る。"""
    b = Briefing(
        task_id=result.task_id,
        verdict=result.evaluation.verdict if result.evaluation else "",
    )

    for ev in result.evaluations:
        asset = store.decisions.get(ev.asset_id)
        if asset is None:
            continue
        b.decisions.append(
            {
                "id": asset.id,
                "version": asset.version,
                "question": asset.question,
                "decision": asset.decision,
                "rationale": asset.rationale.text if asset.rationale.status != "unknown" else None,
                "rationale_status": asset.rationale.status,
                "alternatives": [
                    {"option": a.option, "rejected_because": a.rejected_because}
                    for a in asset.alternatives
                ],
                "governed_by": asset.governed_by,
                "verdict": ev.verdict,
                "conditions": [
                    {
                        "id": ce.condition_id,
                        "statement": ce.statement,
                        "judgment": ce.judgment,
                        "reason": ce.reason,
                    }
                    for ce in ev.condition_evaluations
                ],
            }
        )

    for impl_id in result.reusable_implementations:
        impl = store.implementations.get(impl_id)
        if impl is None:
            continue
        b.implementations.append(
            {
                "id": impl.id,
                "purpose": impl.purpose,
                "entrypoint": impl.implementation.get("entrypoint"),
                "paths": impl.implementation.get("paths", []),
                "requires": impl.compatibility.get("requires", []),
                "runtime": impl.compatibility.get("runtime"),
                "governed_by": impl.governed_by,
            }
        )
        b.snippets.extend(_read_entrypoint(repo, impl))
        for t in impl.verification.get("tests", []):
            cmd = t.get("command")
            if cmd and cmd not in b.verify_commands:
                b.verify_commands.append(cmd)
        b.constraints.extend(str(r) for r in impl.compatibility.get("requires", []))

    for impl_id in result.blocked_implementations:
        b.withheld.append(f"{impl_id}: 判断ゲートが通らなかったため渡さない")

    return b


def to_prompt(b: Briefing) -> str:
    """LLM へ渡す本文。資産が無い群との差はこの本文の有無だけにする。"""
    if not b.decisions and not b.implementations:
        return ""

    lines: list[str] = ["## 過去の Engineering Asset（このリポジトリで既に確定している知識）", ""]
    for d in b.decisions:
        lines.append(f"### 判断 {d['id']} v{d['version']}（現在の再評価: {d['verdict']}）")
        lines.append(f"- 問い: {d['question']}")
        lines.append(f"- 判断: {d['decision']}")
        if d["rationale"]:
            lines.append(f"- 理由: {d['rationale']}")
        for a in d["alternatives"]:
            lines.append(f"- 棄却案: {a['option']} — {a['rejected_because']}")
        lines.append("- 前提の再検証結果（今回このリポジトリで実測した）:")
        for c in d["conditions"]:
            lines.append(f"  - {c['id']} [{c['judgment']}] {c['statement']} … {c['reason']}")
        lines.append("")

    for i in b.implementations:
        lines.append(f"### 実装 {i['id']}")
        lines.append(f"- 目的: {i['purpose']}")
        lines.append(f"- 入口: `{i['entrypoint']}`")
        lines.append(f"- 実行環境: {i['runtime']}")
        for r in i["requires"]:
            lines.append(f"- 満たすべき条件: {r}")
        lines.append("")

    if b.snippets:
        lines.append("### 再利用できる既存実装（実際に読み込んだもの）")
        lines.append("")
        for s in b.snippets:
            if not s.found:
                lines.append(f"- `{s.path}`: {s.note}")
                continue
            lines.append(f"`{s.path}`（{s.note} / 全 {s.lines} 行）")
            lines.append("```typescript")
            lines.append(s.text)
            lines.append("```")
            lines.append("")

    # 同じ節を指す記述が資産ごとに揺れる（註釈の有無など）。
    # 先頭の識別子（ファイル名＋節番号）で畳み、註釈が最も長いものを残す。
    raw = [g for d in b.decisions for g in d.get("governed_by", [])]
    raw += [g for i in b.implementations for g in i.get("governed_by", [])]
    merged: dict[str, str] = {}
    for g in raw:
        key = g.split("（", 1)[0].split("(", 1)[0].strip()
        if key not in merged or len(g) > len(merged[key]):
            merged[key] = g
    governed = sorted(merged.values())
    if governed:
        lines.append("### この領域を統べる上流の要求仕様")
        lines.append("")
        lines.append(
            "**改修に着手する前に、次の箇所を必ず読むこと。** "
            "ここには、この機能の適用範囲や「対象外」の指定が書かれていることがある。"
        )
        lines.append(
            "過去の比較実験で、入口だけを渡された場合に上流要求の「対象外」条項を"
            "見落としたまま実装した例が観測されている。"
        )
        lines.append("")
        for g in governed:
            lines.append(f"- {g}")
        lines.append("")

    if b.verify_commands:
        lines.append("### 検証コマンド（過去にこの実装を通したもの）")
        for c in b.verify_commands:
            lines.append(f"- `{c}`")
        lines.append("")

    if b.withheld:
        lines.append("### 渡していない資産")
        for w in b.withheld:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def run_verification(repo: Path, commands: list[str], timeout: int = 300) -> list[dict]:
    """検証コマンドを実際に走らせる。成否は終了コードで決める。

    「エージェントが落ちなかった」を成功とみなさない（OrcaReplay の --verify と同じ立場）。
    """
    out: list[dict] = []
    for cmd in commands:
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=repo, capture_output=True, text=True, timeout=timeout
            )
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
            out.append(
                {
                    "command": cmd,
                    "exit_code": proc.returncode,
                    "passed": proc.returncode == 0,
                    "tail": [t.strip()[:200] for t in tail],
                }
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            out.append(
                {
                    "command": cmd, "exit_code": -1, "passed": False,
                    "tail": [f"実行できなかった: {type(exc).__name__}"],
                }
            )
    return out
