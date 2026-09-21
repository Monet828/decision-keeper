"""普段の開発に寄り添う常時運用（start / finish）。

実験のための特別なセットアップではなく、普段の作業の前後に1コマンドずつ挟むだけで
- 着手時: 資産を検索し、条件を現在のコードで再検証し、手渡し資料を出す
- 完了時: 差分と検証結果を記録し、資産候補を抽出し、予測と実際の一致を台帳へ残す
が回るようにする。

A/B の定量比較はここでは行わない（毎回の作業を2倍にしないため）。
ここで積むのは「機械が出した判断が当たったか外れたか」の実績。
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from .assets_v2 import briefing as briefing_mod
from .assets_v2.agent import Task
from .assets_v2.agent import run as run_agent
from .assets_v2.store import AssetStore, StoreError
from .experience.recorder import Recorder

LEDGER_NAME = "ledger.jsonl"


class Prediction(BaseModel):
    """着手時点で機械が出した判断。後から書き換えない。"""

    verdict: str = ""
    asset_ids: list[str] = Field(default_factory=list)
    reusable_implementations: list[str] = Field(default_factory=list)
    contradicted: list[str] = Field(default_factory=list)
    insufficient: list[str] = Field(default_factory=list)
    not_observed: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    briefing_chars: int = 0


class Outcome(BaseModel):
    """完了時点で観測できた事実と、人の評価。"""

    changed_paths: list[str] = Field(default_factory=list)
    verify: list[dict] = Field(default_factory=list)
    candidates: list[str] = Field(default_factory=list)
    # 機械では決められない。人が後から埋める。
    human_assessment: str = "unrecorded"  # matched | diverged | not_applicable
    note: str = ""


class SessionState(BaseModel):
    task_id: str
    repo: str
    run_id: str
    started_at: str
    base_commit: str | None = None
    base_branch: str | None = None
    finished_at: str | None = None
    head_commit: str | None = None
    prediction: Prediction = Field(default_factory=Prediction)
    outcome: Outcome = Field(default_factory=Outcome)


def _git(repo: Path, *args: str) -> str | None:
    try:
        p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=30)
        return p.stdout.strip() if p.returncode == 0 else None
    except OSError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _state_path(root: Path, task_id: str) -> Path:
    return root / "sessions" / f"{task_id}.json"


def start(
    root: Path,
    assets_dir: Path,
    repo: Path,
    task_id: str,
    task_text: str,
    diff_text: str = "",
) -> tuple[SessionState, str]:
    """着手時。資産を引き当て、条件を再検証し、手渡し資料を返す。"""
    state_path = _state_path(root, task_id)
    if state_path.exists():
        raise FileExistsError(f"このタスクは既に開始されています: {state_path}")

    rec = Recorder(root / "experience", run_id=None, cwd=repo)
    rec.target_repo(repo)
    rec.note(task_text, kind="task")

    prediction = Prediction()
    brief_text = ""
    try:
        store = AssetStore.load(assets_dir)
    except StoreError as exc:
        rec.note(f"資産を読めなかった: {exc}", kind="asset_error")
        store = None

    if store is not None:
        result = run_agent(store, Task(id=task_id, description=task_text, diff=diff_text), repo)
        b = briefing_mod.build(store, result, repo)
        brief_text = briefing_mod.to_prompt(b)

        by = {"contradicted": [], "insufficient": [], "not_observed": []}
        for ev in result.evaluations:
            for ce in ev.condition_evaluations:
                if ce.judgment in by:
                    by[ce.judgment].append(f"{ev.asset_id}/{ce.condition_id}")

        prediction = Prediction(
            verdict=result.evaluation.verdict if result.evaluation else "no_asset",
            asset_ids=[e.asset_id for e in result.evaluations],
            reusable_implementations=result.reusable_implementations,
            contradicted=by["contradicted"],
            insufficient=by["insufficient"],
            not_observed=by["not_observed"],
            human_review_required=result.engineering_context.human_review_required,
            briefing_chars=len(brief_text),
        )
        rec.note(
            json.dumps(prediction.model_dump(), ensure_ascii=False),
            kind="prediction",
        )
        for n in result.notes:
            rec.note(n, kind="agent_note")

    state = SessionState(
        task_id=task_id,
        repo=str(repo),
        run_id=rec.run_id,
        started_at=_now(),
        base_commit=_git(repo, "rev-parse", "HEAD"),
        base_branch=_git(repo, "branch", "--show-current"),
        prediction=prediction,
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    if brief_text:
        brief_path = root / "briefings" / f"{task_id}.md"
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(brief_text, encoding="utf-8")
    return state, brief_text


def finish(
    root: Path,
    repo: Path,
    task_id: str,
    verify_commands: list[str] | None = None,
    assessment: str = "unrecorded",
    note: str = "",
) -> SessionState:
    """完了時。差分と検証結果を記録し、候補を抽出し、台帳へ積む。"""
    state_path = _state_path(root, task_id)
    if not state_path.exists():
        raise FileNotFoundError(f"開始記録がありません: {state_path}")
    state = SessionState.model_validate_json(state_path.read_text(encoding="utf-8"))

    rec = Recorder.resume(root / "experience" / "runs" / state.run_id)
    rec.next_turn()

    # 着手時点からの差分を記録する
    base = state.base_commit or "HEAD"
    changed = (_git(repo, "diff", "--name-only", base) or "").splitlines()
    changed = [c for c in changed if c.strip()]
    for path in changed:
        diff = _git(repo, "diff", base, "--", path) or ""
        if diff:
            rec.fs_change(path, "modified", diff)

    # 検証を実際に走らせる。落ちなかったことを成功とみなさない。
    verify: list[dict] = []
    for cmd in verify_commands or []:
        code, out = rec.shell(cmd.split())
        verify.append({"command": cmd, "exit_code": code, "passed": code == 0,
                       "tail": out.strip().splitlines()[-5:]})

    if note:
        rec.note(note, kind="outcome_note")
    rec.close(exit_code=0)

    # 候補を抽出する
    from .experience.extractor import analyse, write_candidates
    from .experience.reader import TraceReader

    reader = TraceReader.open(root / "experience" / "runs" / state.run_id)
    ex = analyse(reader)
    cand_dir = root / "candidates" / task_id
    candidates = [p.name for p in write_candidates(ex, reader, cand_dir)]

    state.finished_at = _now()
    state.head_commit = _git(repo, "rev-parse", "HEAD")
    state.outcome = Outcome(
        changed_paths=changed,
        verify=verify,
        candidates=candidates,
        human_assessment=assessment,
        note=note,
    )
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    with (root / LEDGER_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(state.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return state


def read_ledger(root: Path) -> list[SessionState]:
    path = root / LEDGER_NAME
    if not path.exists():
        return []
    out: list[SessionState] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(SessionState.model_validate_json(line))
            except Exception:  # noqa: BLE001
                continue
    return out


def ledger_summary(root: Path) -> str:
    rows = read_ledger(root)
    if not rows:
        return "台帳はまだ空です。"

    lines = ["| タスク | 機械の判断 | 指摘した前提 | 検証 | 人の評価 |", "|---|---|---|---|---|"]
    counts = {"matched": 0, "diverged": 0, "unrecorded": 0, "not_applicable": 0}
    flagged = 0
    for s in rows:
        p, o = s.prediction, s.outcome
        issues = p.contradicted + p.insufficient + p.not_observed
        if issues:
            flagged += 1
        v = "・".join(
            ("通過" if x["passed"] else f"失敗({x['exit_code']})") for x in o.verify
        ) or "-"
        counts[o.human_assessment] = counts.get(o.human_assessment, 0) + 1
        issue_text = "、".join(issues) or "なし"
        lines.append(
            f"| {s.task_id} | {p.verdict} | {issue_text} | {v} | {o.human_assessment} |"
        )
    lines.append("")
    lines.append(f"- 記録数: {len(rows)}")
    lines.append(f"- 前提の崩れを指摘した回数: {flagged}")
    lines.append(
        "- 人の評価: "
        + "、".join(f"{k}={v}" for k, v in counts.items() if v)
    )
    lines.append("")
    lines.append("`unrecorded` は人がまだ評価していないという意味であり、成功でも失敗でもない。")
    return "\n".join(lines)
