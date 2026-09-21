"""Experience から Asset Candidate を抽出する（原典§12）。

trace から直接 Approved Asset を作ってはならない。必ず candidate を経由する。

抽出は決定論的に行う範囲と、記述が必要な範囲を分ける。
- 決定論的に取れるもの: 変更したパス、実行したコマンド、終了コード、
  「赤 -> 変更 -> 緑」の遷移、provenance
- trace に明示されていないもの: なぜそうしたか。
  これは推測で埋めず `rationale.status: unknown` として残す（EA-07）。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..assets_v2.schema import (
    Condition,
    DecisionAsset,
    ImplementationAsset,
    Provenance,
    Rationale,
    Verifier,
)
from .reader import Event, TraceReader

PLACEHOLDER = "[要記述]"


class TestTransition(BaseModel):
    """テストが失敗から成功へ変わった区間。実装資産の根拠になる。"""

    failed_at: int
    passed_at: int
    command: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)


class CommandOutcome(BaseModel):
    """検証コマンド1つの最終結果。最後の実行を採る。"""

    command: list[str] = Field(default_factory=list)
    last_exit_code: int = -1
    last_seq: int = -1
    ran_after_last_source_change: bool = False

    @property
    def passed(self) -> bool:
        return self.last_exit_code == 0


class TargetRepo(BaseModel):
    path: str = ""
    head: str | None = None
    branch: str | None = None
    source: str = "unknown"  # explicit | inferred_from_shell_cwd | manifest


class Extraction(BaseModel):
    run_id: str
    adapter_id: str
    target: TargetRepo = Field(default_factory=TargetRepo)
    source_paths: list[str] = Field(default_factory=list)
    test_paths: list[str] = Field(default_factory=list)
    doc_paths: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    test_commands: list[list[str]] = Field(default_factory=list)
    outcomes: list[CommandOutcome] = Field(default_factory=list)
    transitions: list[TestTransition] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    integrity_ok: bool = False
    problems: list[str] = Field(default_factory=list)

    @property
    def verified_commands(self) -> list[CommandOutcome]:
        """検証根拠として使えるコマンド。

        最後の実行が成功し、かつ最後のソース変更より後に走ったものだけ。
        失敗したままのコマンドは根拠にしない。
        """
        return [o for o in self.outcomes if o.passed and o.ran_after_last_source_change]


TEST_PATH_HINTS = ("test", "spec", "__tests__")
DOC_PATH_HINTS = ("docs/", "doc/", ".md")


def _classify(path: str) -> str:
    low = path.lower()
    if any(h in low for h in TEST_PATH_HINTS):
        return "test"
    if any(low.endswith(h) or h in low for h in DOC_PATH_HINTS):
        return "doc"
    return "source"


def _is_test(event: Event) -> bool:
    argv = [str(a).lower() for a in event.attrs.get("argv", [])]
    joined = " ".join(argv)
    return any(k in joined for k in ("test", "pytest", "vitest", "jest"))


def _target_repo(reader: TraceReader) -> TargetRepo:
    """作業対象のリポジトリを決める。

    manifest の cwd は CLI を起動した場所であり作業対象とは限らないため、
    明示された target_repo note を最優先で見る。
    """
    for e in reader.by_type("note"):
        if e.attrs.get("kind") == "target_repo":
            return TargetRepo(
                path=str(e.attrs.get("path", "")),
                head=e.attrs.get("head"),
                branch=e.attrs.get("branch"),
                source="explicit",
            )
    cwds = [str(e.attrs.get("cwd")) for e in reader.by_type("shell.exec") if e.attrs.get("cwd")]
    if cwds:
        common = max(set(cwds), key=cwds.count)
        return TargetRepo(path=common, source="inferred_from_shell_cwd")
    git = reader.manifest.get("git") or {}
    return TargetRepo(
        path=str(reader.manifest.get("cwd", "")),
        head=git.get("head"),
        branch=git.get("branch"),
        source="manifest",
    )


def analyse(reader: TraceReader) -> Extraction:
    """trace から決定論的に読み取れる事実だけを集める。"""
    ok, why = reader.verify_integrity()
    problems = list(reader.problems)
    if not ok and why:
        problems.append(why)

    changed = sorted({
        str(e.attrs.get("path")) for e in reader.by_type("fs.change") if e.attrs.get("path")
    })
    buckets: dict[str, list[str]] = {"source": [], "test": [], "doc": []}
    for path in changed:
        buckets[_classify(path)].append(path)

    last_source_seq = max(
        (e.seq for e in reader.by_type("fs.change")
         if _classify(str(e.attrs.get("path", ""))) == "source"),
        default=-1,
    )

    exec_by_seq = {e.seq: e for e in reader.by_type("shell.exec")}
    test_cmds: list[list[str]] = []
    results: list[tuple[int, int, list[str]]] = []  # (seq, exit_code, argv)
    for res in reader.by_type("shell.result"):
        src = next((exec_by_seq[c] for c in res.causes if c in exec_by_seq), None)
        if src is None or not _is_test(src):
            continue
        argv = [str(a) for a in src.attrs.get("argv", [])]
        if argv not in test_cmds:
            test_cmds.append(argv)
        results.append((res.seq, int(res.attrs.get("exit_code", -1)), argv))

    # 「赤 -> 緑」の遷移を探す。その間の fs.change が実装資産の根拠。
    transitions: list[TestTransition] = []
    for i, (seq, code, argv) in enumerate(results):
        if code == 0:
            continue
        for later_seq, later_code, later_argv in results[i + 1:]:
            if later_code == 0 and later_argv == argv:
                between = [
                    str(e.attrs.get("path"))
                    for e in reader.by_type("fs.change")
                    if seq < e.seq < later_seq and e.attrs.get("path")
                ]
                transitions.append(
                    TestTransition(
                        failed_at=seq, passed_at=later_seq,
                        command=argv, changed_paths=sorted(set(between)),
                    )
                )
                break

    # コマンドごとの最終結果。同じコマンドが複数回走った場合は最後を採る。
    by_cmd: dict[tuple[str, ...], CommandOutcome] = {}
    for seq, code, argv in results:
        key = tuple(argv)
        by_cmd[key] = CommandOutcome(
            command=argv, last_exit_code=code, last_seq=seq,
            ran_after_last_source_change=(seq > last_source_seq),
        )
    outcomes = sorted(by_cmd.values(), key=lambda o: o.last_seq)

    notes = [
        reader.payload_text(e) for e in reader.by_type("note")
        if e.attrs.get("kind") != "target_repo"
    ]

    if not any(o.passed and o.ran_after_last_source_change for o in outcomes):
        problems.append(
            "ソース変更後に成功した検証コマンドが無い。実装資産の検証根拠を作れない"
        )

    return Extraction(
        run_id=reader.run_id,
        adapter_id=reader.adapter_id,
        target=_target_repo(reader),
        source_paths=buckets["source"],
        test_paths=buckets["test"],
        doc_paths=buckets["doc"],
        changed_paths=changed,
        test_commands=test_cmds,
        outcomes=outcomes,
        transitions=transitions,
        notes=[n for n in notes if n.strip()],
        integrity_ok=ok,
        problems=problems,
    )


def _globs(paths: list[str], limit: int = 5) -> list[str]:
    """パス一覧を重複のない glob へ畳む。"""
    out: list[str] = []
    for p in paths:
        g = f"{p.rsplit('/', 1)[0]}/*" if "/" in p else p
        if g not in out:
            out.append(g)
    return out[:limit]


def _provenance(ex: Extraction, reader: TraceReader) -> list[Provenance]:
    prov = [Provenance(type="orca_run", ref=ex.run_id, note=f"adapter={ex.adapter_id}")]
    if ex.target.head:
        prov.append(
            Provenance(
                type="commit", ref=ex.target.head,
                note=f"{ex.target.path} ({ex.target.source})",
            )
        )
    for t in ex.transitions:
        prov.append(
            Provenance(
                type="test_result", ref=" ".join(t.command),
                note=f"seq {t.failed_at} で失敗、seq {t.passed_at} で成功",
            )
        )
    # 赤->緑が無くても、変更後に成功した検証は根拠になる
    for o in ex.verified_commands:
        if any(p.ref == " ".join(o.command) for p in prov):
            continue
        prov.append(
            Provenance(
                type="test_result", ref=" ".join(o.command),
                note=f"ソース変更後の seq {o.last_seq} で終了コード 0",
            )
        )
    return prov


def to_implementation_candidate(
    ex: Extraction, reader: TraceReader, purpose: str = ""
) -> ImplementationAsset:
    """実装資産の候補。検証を通過した事実が根拠になる。"""
    paths = ex.source_paths or ex.changed_paths
    return ImplementationAsset(
        id=f"IMP-C-{ex.run_id.replace('run_', '')[:8]}",
        status="candidate",
        version=1,
        decided_at=date.today(),
        purpose=purpose or PLACEHOLDER,
        implementation={
            "repository": ex.target.path or PLACEHOLDER,
            "commit": ex.target.head or PLACEHOLDER,
            "branch": ex.target.branch,
            "paths": paths,
            "entrypoint": PLACEHOLDER,
        },
        compatibility={"runtime": PLACEHOLDER, "dependencies": [], "requires": []},
        verification={
            # 検証根拠は「ソース変更後に成功した実行」に限る。
            # 失敗したままのコマンドを passed として記録しない。
            "tests": [
                {
                    "command": " ".join(o.command),
                    "paths": ex.test_paths,
                    "last_result": "passed",
                    "evidence": f"ソース変更後の seq {o.last_seq} で終了コード 0",
                }
                for o in ex.verified_commands
            ],
            # 失敗したまま終わったコマンドも隠さず残す。
            "known_failing": [
                {"command": " ".join(o.command), "exit_code": o.last_exit_code}
                for o in ex.outcomes
                if not o.passed
            ],
        },
        provenance=_provenance(ex, reader),
        applies_to={"paths": _globs(paths), "keywords": []},
    )


def to_decision_candidate(ex: Extraction, reader: TraceReader) -> DecisionAsset:
    """判断資産の候補。

    trace には「何が起きたか」しかない。「なぜそうしたか」は note に人が
    書いたぶんしか残らないため、rationale は原則 unknown のままにする（EA-07）。
    """
    has_reason = bool(ex.notes)
    conditions = [
        Condition(
            id=f"C{i + 1}",
            statement=f"検証コマンド `{' '.join(o.command)}` が通過する",
            expectation="present",
            verifier=Verifier(
                type="test",
                targets=ex.source_paths or ex.changed_paths,
                patterns=[" ".join(o.command)],
                note="trace で観測した検証コマンド",
            ),
            source=f"{ex.run_id} seq {o.last_seq}",
        )
        for i, o in enumerate(ex.verified_commands)
    ]

    return DecisionAsset(
        id=f"DEC-C-{ex.run_id.replace('run_', '')[:8]}",
        status="candidate",
        version=1,
        decided_at=date.today(),
        question=PLACEHOLDER,
        decision=PLACEHOLDER,
        rationale=(
            Rationale(status="needs_review", text="\n".join(ex.notes)[:2000])
            if has_reason
            else Rationale(status="unknown")
        ),
        conditions=conditions,
        provenance=_provenance(ex, reader),
        applies_to={"paths": _globs(ex.source_paths or ex.changed_paths), "keywords": []},
    )


def write_candidates(
    ex: Extraction, reader: TraceReader, out_dir: Path, purpose: str = ""
) -> list[Path]:
    """候補をYAMLで書き出す。既存資産には一切触れない。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    header = (
        "# Experience から自動抽出した候補。未承認。\n"
        f"# 出典: {ex.run_id} (adapter={ex.adapter_id})\n"
        "# trace に明示されていない項目は [要記述] または unknown のまま残している。\n"
        "# 人が埋め、status を approved、approved_by を実名に変えるまで通常検索に出ない。\n"
    )
    for asset in (
        to_implementation_candidate(ex, reader, purpose),
        to_decision_candidate(ex, reader),
    ):
        path = out_dir / f"{asset.id}.yaml"
        body = yaml.safe_dump(
            asset.model_dump(mode="json", exclude_none=True),
            allow_unicode=True, sort_keys=False,
        )
        path.write_text(header + body, encoding="utf-8")
        written.append(path)
    return written
