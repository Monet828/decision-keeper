"""Engineering Assets v0.1 の要件 EA-01〜EA-12 の適合検査。"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from app.decision_keeper import approve, scope
from conftest import ROOT
from pydantic import ValidationError

from decision_keeper.assets_v2 import briefing as briefing_mod
from decision_keeper.assets_v2 import context as ctx_mod
from decision_keeper.assets_v2 import verifiers
from decision_keeper.assets_v2.agent import Task, run
from decision_keeper.assets_v2.evaluate import decide_verdict, evaluate_condition
from decision_keeper.assets_v2.schema import (
    Condition,
    ConditionEvaluation,
    DecisionAsset,
    Evidence,
    Verifier,
)
from decision_keeper.assets_v2.store import AssetStore

EA = ROOT / "tests" / "fixtures" / "ea"
ASSETS = EA / "assets"
TASKS = EA / "tasks"


def _task(name: str) -> tuple[Task, Path]:
    d = TASKS / name
    return (
        Task(
            id=name,
            description=(d / "task.md").read_text(encoding="utf-8"),
            diff=(d / "diff.patch").read_text(encoding="utf-8"),
        ),
        d / "repo",
    )


def _run(name: str, include_candidates: bool = False):
    store = AssetStore.load(ASSETS, include_candidates=include_candidates)
    task, repo = _task(name)
    return run(store, task, repo)


# --- EA-01 / EA-02: lifecycle ---

def test_lifecycle_states_are_preserved():
    """EA-01: 4状態を保持する。"""
    store = AssetStore.load(ASSETS, include_candidates=True)
    statuses = {a.id: a.status for a in store.decisions.values()}
    assert statuses["DEC-007"] == "approved"
    assert statuses["DEC-C900"] == "candidate"


def test_candidates_are_not_searchable():
    """EA-02: candidate は通常検索で返してはならない。"""
    store = AssetStore.load(ASSETS)
    assert "DEC-C900" not in store.decisions
    assert any("DEC-C900" in s for s in store.skipped)

    hits = store.search_decisions(["src/auth/permissions.py"], "キャッシュ 権限")
    assert all(a.id != "DEC-C900" for a, _ in hits)


def test_candidates_readable_only_when_explicit():
    """EA-02: 明示したときだけ読める。"""
    store = AssetStore.load(ASSETS, include_candidates=True)
    assert "DEC-C900" in store.decisions


# --- EA-03: Approved は書き換えない ---

def test_approved_assets_are_not_modified(tmp_path):
    """EA-03: 実行前後で approved 資産のSHA-256が不変。"""
    work = tmp_path / "assets"
    shutil.copytree(ASSETS, work)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in work.glob("*.yaml")}

    store = AssetStore.load(work)
    task, repo = _task("T2-conflict")
    run(store, task, repo)

    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in work.glob("*.yaml")}
    assert before == after
    unchanged, changed = store.verify_unchanged()
    assert unchanged and not changed


def test_tampering_is_detected(tmp_path):
    """EA-03: 実行中の書き換えを検出する。"""
    work = tmp_path / "assets"
    shutil.copytree(ASSETS, work)
    store = AssetStore.load(work)
    target = work / "DEC-007.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    unchanged, changed = store.verify_unchanged()
    assert not unchanged and changed


def test_supersedes_is_representable():
    """EA-03: 変更は新版＋supersedes で表せる。"""
    v2 = DecisionAsset(
        id="DEC-007", version=2, status="candidate",
        supersedes=["DEC-007-v1"], question="q", decision="d",
    )
    assert v2.supersedes == ["DEC-007-v1"]


# --- EA-04: Evidence に判断を含めない ---

def test_evidence_has_no_judgment_field():
    """EA-04: Evidence のスキーマに判断相当のフィールドが無い。"""
    fields = set(Evidence.model_fields)
    assert not (fields & {"judgment", "verdict", "status", "supported", "confidence"})


# --- EA-05 / EA-06: judgment 4種と、0件と未観測の区別 ---

@pytest.mark.parametrize("judgment", ["supported", "contradicted", "insufficient", "not_observed"])
def test_all_four_judgments_are_expressible(judgment):
    """EA-05: 4種すべてを出せる。"""
    ce = ConditionEvaluation(condition_id="C1", judgment=judgment)
    assert ce.judgment == judgment


def test_scanned_zero_is_positive_evidence_for_absent():
    """EA-06: 探索して0件は expectation=absent に対し supported。"""
    cond = Condition(
        id="C1", statement="機構が無い", expectation="absent",
        verifier=Verifier(type="grep", targets=["src/auth/*"], patterns=["invalidate"]),
    )
    ev = verifiers.run(TASKS / "T1-inherit" / "repo", cond)
    assert ev.type == "grep_result"
    assert ev.observation["files_scanned"] > 0
    assert ev.observation["matches"] == 0
    assert evaluate_condition(cond, ev).judgment == "supported"


def test_not_scanned_is_not_observed():
    """EA-06: 探索していない場合は not_observed。supported にしない。"""
    cond = Condition(
        id="C1", statement="x", expectation="absent",
        verifier=Verifier(type="grep", targets=["does/not/exist/*"], patterns=["x"]),
    )
    ev = verifiers.run(TASKS / "T1-inherit" / "repo", cond)
    assert ev.type == "not_observed"
    assert evaluate_condition(cond, ev).judgment == "not_observed"


def test_file_exists_absent_can_be_supported():
    """EA-06: file_exists でも「探索して無かった」は supported に到達できること。

    回帰の由来: files_scanned に一致件数を入れていたため、ファイルが無いと
    scanned=0 になり not_observed へ落ちた。expectation: absent が原理的に
    成立しなくなっていた（DEC-004 C1 で実測）。
    """
    cond = Condition(
        id="C1", statement="設定ファイルが無い", expectation="absent",
        verifier=Verifier(type="file_exists", targets=["vercel.json"]),
    )
    ev = verifiers.run(TASKS / "T1-inherit" / "repo", cond)
    assert ev.type == "file_list"
    assert ev.observation["matches"] == 0
    assert ev.observation["files_scanned"] > 0
    assert evaluate_condition(cond, ev).judgment == "supported"


def test_file_exists_missing_repo_is_not_observed():
    """探索が成立しない場合は supported にしない。"""
    cond = Condition(
        id="C1", statement="設定ファイルが無い", expectation="absent",
        verifier=Verifier(type="file_exists", targets=["vercel.json"]),
    )
    ev = verifiers.run(TASKS / "no-such-repo-xyz", cond)
    assert ev.type == "not_observed"
    assert evaluate_condition(cond, ev).judgment == "not_observed"


def test_finish_runs_verify_in_target_repo():
    """finish の検証コマンドは --repo で走ること（manifest.cwd で走らせない）。

    構造で固定する。実際に npm を走らせるテストは環境依存になるため、
    「cwd を明示している」ことをソース上で確認する。

    回帰の由来: Recorder.resume は self.cwd を manifest.cwd（= CLI を起動した場所。
    作業対象とは限らない）から復元する。finish が cwd を明示していなかったため、
    検証コマンドが別リポジトリで実行され、reel-auto では通る `npm run -s typecheck` が
    終了コード 254 の**偽の失敗**として台帳に記録された（2026-09-22、p105-w3-auth で実測）。
    Extractor で同型の取り違えを直した際、検証コマンドの実行経路を見落としていた。
    """
    from pathlib import Path

    from app.decision_keeper import session as session_mod

    src = Path(session_mod.__file__).read_text(encoding="utf-8")
    assert "rec.shell(cmd.split(), cwd=repo)" in src, (
        "finish の検証コマンドが cwd=repo を明示していない。"
        "manifest.cwd で走ると別リポジトリで検証してしまう"
    )


# --- EA-07: 補完してはならない ---

def test_rationale_unknown_is_allowed_and_known_requires_text():
    """EA-07: 確認できない理由は unknown のまま保持できる。known には text が要る。"""
    from decision_keeper.assets_v2.schema import Rationale

    assert Rationale(status="unknown").text == ""
    with pytest.raises(ValidationError):
        Rationale(status="known", text="")


def test_claim_without_observation_is_insufficient():
    """EA-07: 主張はあるが観測が裏付けない場合、supported にも contradicted にもしない。"""
    result = _run("T3-unsupported")
    ce = next(
        c for e in result.evaluations for c in e.condition_evaluations if c.condition_id == "C1"
    )
    assert ce.judgment == "insufficient"


# --- EA-08: 自動確認不能なら human_review_required ---

def test_human_verifier_sets_review_required_and_holds():
    """EA-08: human verifier を含むと human_review_required かつ hold。"""
    result = _run("T4-human")
    assert result.engineering_context.human_review_required is True
    assert result.evaluation.verdict == "hold"


def test_human_review_blocks_autonomous_reuse():
    """EA-08: 人の確認が必要なとき、実装資産を再利用可にしない。"""
    result = _run("T4-human")
    assert result.reusable_implementations == []
    assert "IMP-018" in result.blocked_implementations


# --- EA-09: Implementation と Decision の relation ---

def test_relation_is_traversable_both_ways():
    """EA-09: 双方向にたどれる。"""
    store = AssetStore.load(ASSETS)
    assert [d.id for d in store.decisions_for_implementation("IMP-018")] == ["DEC-007"]
    rels = {r.id for r, _ in store.related("DEC-007")}
    assert "IMP-018" in rels


def test_decision_only_and_implementation_only_are_allowed(tmp_path):
    """EA-09: 片方だけの存在も許容する。"""
    work = tmp_path / "assets"
    work.mkdir()
    shutil.copy(ASSETS / "IMP-018.yaml", work)
    store = AssetStore.load(work)
    assert "IMP-018" in store.implementations
    assert store.decisions == {}
    # 相手が存在しない relation は None として返る
    assert [other for _, other in store.related("IMP-018")] == [None]


# --- EA-10: provenance ---

def test_approved_requires_provenance():
    """EA-10: provenance の無い Asset は approved にできない。"""
    with pytest.raises(ValidationError):
        DecisionAsset(
            id="X", status="approved", approved_by="me", question="q", decision="d",
        )


def test_fixtures_have_traceable_provenance():
    """EA-10: 同梱資産は出典をたどれる。"""
    store = AssetStore.load(ASSETS)
    for asset in list(store.decisions.values()) + list(store.implementations.values()):
        assert asset.provenance, f"{asset.id} に provenance が無い"
        assert all(p.ref for p in asset.provenance)


# --- EA-11: Asset Layer はモデル選択をしない ---

def test_asset_layer_has_no_model_selection():
    """EA-11: Engineering Context にモデル選択が含まれない（原典§16）。"""
    fields = set(ctx_mod.EngineeringContext.model_fields)
    assert not (fields & {"selected_model", "model", "difficulty"})
    assert not hasattr(ctx_mod, "select_model")

    src = Path(ctx_mod.__file__).read_text(encoding="utf-8")
    for name in ("deepseek", "anthropic", "claude-sonnet", "gpt-"):
        assert name not in src.lower(), f"Asset Layer にモデル名 {name} が含まれている"


def test_engineering_context_exposes_required_flags():
    """EA-11: 原典§16 のフラグを出す。"""
    result = _run("T2-conflict")
    c = result.engineering_context
    assert c.asset_found is True
    assert c.decision_conflict is True
    assert c.reuse_possible is False
    headers = c.to_headers()
    assert headers["X-Engineering-Decision-Conflict"] == "1"


# --- EA-12: 検索 → 検証 → verdict ---

@pytest.mark.parametrize(
    "task,verdict,exit_code",
    [
        ("T1-inherit", "inherit", 0),
        ("T2-conflict", "propose_update", 10),
        ("T3-unsupported", "hold", 20),
        ("T4-human", "hold", 20),
    ],
)
def test_execution_agent_returns_expected_verdict(task, verdict, exit_code):
    """EA-12: Task に対し Asset を検索し Condition を検証して verdict を返す。"""
    result = _run(task)
    assert result.evaluation.verdict == verdict
    assert result.exit_code == exit_code


def test_all_matching_assets_are_evaluated():
    """広い Asset が他を覆い隠さないこと。"""
    result = _run("T4-human")
    ids = {e.asset_id for e in result.evaluations}
    assert {"DEC-007", "DEC-009"} <= ids


def test_reuse_allowed_only_when_inherit():
    """判断ゲートが inherit のときだけ実装資産を再利用可にする。"""
    assert _run("T1-inherit").reusable_implementations == ["IMP-018"]
    for name in ("T2-conflict", "T3-unsupported", "T4-human"):
        assert _run(name).reusable_implementations == []


# --- verdict 規則 ---

@pytest.mark.parametrize(
    "judgment,verdict",
    [
        ("supported", "inherit"),
        ("contradicted", "propose_update"),
        ("insufficient", "hold"),
        ("not_observed", "hold"),
    ],
)
def test_verdict_rules(judgment, verdict):
    ce = [ConditionEvaluation(condition_id="C1", judgment=judgment)]
    assert decide_verdict(ce, False)[0] == verdict


def test_missing_asset_yields_evidence_gap(tmp_path):
    """適用範囲がリポジトリに無ければ、差分が無くても evidence_gap になる。

    ⚠ 2026-09-23 に条件を変えた（EA-13）。以前はここで T1-inherit/repo を使い
    「説明が無関係なら何も引かない」を確かめていたが、あの repo は
    src/auth/ と src/cache/ を実際に持つため、**範囲照合では当たるのが正しい**。
    テストが見たいのは「該当が無いときに evidence_gap が立つ」ことなので、
    範囲が本当に存在しない repo へ対象を移した。
    """
    empty_repo = tmp_path / "empty"
    (empty_repo / "docs").mkdir(parents=True)
    (empty_repo / "docs" / "readme.md").write_text("何もない", encoding="utf-8")

    store = AssetStore.load(ASSETS)
    task = Task(id="T9", description="無関係な作業", diff="")
    result = run(store, task, empty_repo)
    assert result.evaluation is None
    assert result.engineering_context.asset_found is False
    assert result.engineering_context.evidence_gap is True
    assert result.exit_code == 20


def test_no_diff_run_now_surfaces_assets_governing_the_repo():
    """EA-13 の本体。検証専用の run でも、その repo を統べる Asset が出ること。

    以前はここが no_asset になり、台帳の 3 件中 2 件が空振りしていた。
    """
    store = AssetStore.load(ASSETS)
    task = Task(id="T9", description="無関係な作業", diff="")
    result = run(store, task, TASKS / "T1-inherit" / "repo")

    assert result.evaluation is not None, "repo に src/auth・src/cache がある以上、引けるべき"
    assert result.engineering_context.asset_found is True
    reasons = " ".join(n for n in result.notes)
    assert result.evaluation.asset_id.startswith("DEC-")


# --- EA-13: 差分が無い Task でも適用範囲で検索できる（2026-09-23） ---


def _scope_asset(tmp_path):
    """applies_to.paths だけを持ち、キーワードでは当たらない Asset を1件作る。"""
    d = tmp_path / "assets"
    d.mkdir(parents=True, exist_ok=True)
    (d / "DEC-S1.yaml").write_text(
        "\n".join(
            [
                "id: DEC-S1",
                "type: decision",
                "question: 範囲照合を確認できるか",
                "decision: 範囲照合で引けること",
                "status: approved",
                "approved_by: test",
                "provenance:",
                "  - type: adr",
                "    ref: docs/specs/engineering-assets-v0.1.md",
                "applies_to:",
                "  paths: ['src/server/*']",
                "  keywords: ['zzz_never_matches']",
                "conditions:",
                "  - id: C1",
                "    status: active",
                "    statement: src/server 配下が存在すること",
                "    expectation: present",
                "    verifier:",
                "      type: file_exists",
                "      targets: ['src/server/index.ts']",
            ]
        ),
        encoding="utf-8",
    )
    return d


def _repo_with_server(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src" / "server").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "server" / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
    return repo


def test_no_diff_task_still_finds_asset_by_scope(tmp_path):
    """差分0件の Task でも、適用範囲がリポジトリに実在すれば検索に出る（EA-13）。

    これが無いと、着手時(start)と検証専用の run が常に no_asset になる。
    """
    store = AssetStore.load(_scope_asset(tmp_path))
    repo = _repo_with_server(tmp_path)

    result = run(store, Task(id="t", description="関係ない説明", diff=""), repo)

    assert result.evaluation is not None, "差分が無くても Asset が引けること"
    assert result.evaluation.asset_id == "DEC-S1"


def test_scope_match_is_labelled_distinctly(tmp_path):
    """変更パスで当たったのか、範囲の実在で当たったのかを理由文で区別できること。"""
    store = AssetStore.load(_scope_asset(tmp_path))
    repo = _repo_with_server(tmp_path)
    paths = scope.repo_paths(repo)

    hits = store.search_decisions([], "説明", paths)
    assert len(hits) == 1
    assert "適用範囲がリポジトリに存在" in hits[0][1]
    assert "変更パスの一致" not in hits[0][1]


def test_scope_match_is_not_applied_when_diff_exists(tmp_path):
    """差分があるときは範囲照合を足さない。広い Asset があらゆる変更に当たるのを防ぐ。"""
    store = AssetStore.load(_scope_asset(tmp_path))
    repo = _repo_with_server(tmp_path)
    paths = scope.repo_paths(repo)

    # src/server 配下に当たらない変更。従来どおり何も引かない。
    diff = "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-a\n+b\n"
    changed = Task(id="t", diff=diff).changed_paths
    assert changed == ["README.md"]
    assert store.search_decisions(changed, "説明", paths) == []


def test_repo_paths_excludes_untracked_noise(tmp_path):
    """git 管理外の生成物を範囲照合の母数に入れない。"""
    repo = _repo_with_server(tmp_path)
    (repo / "node_modules" / "junk").mkdir(parents=True, exist_ok=True)
    (repo / "node_modules" / "junk" / "a.ts").write_text("x", encoding="utf-8")

    paths = scope.repo_paths(repo)
    assert "src/server/index.ts" in paths
    assert not any(p.startswith("node_modules/") for p in paths)


# --- EA-14: Condition を持たない判断は参照メモとして扱う（2026-09-23） ---


def _note_asset(tmp_path, with_conditions: bool = False):
    d = tmp_path / "assets"
    d.mkdir(parents=True, exist_ok=True)
    lines = [
        "id: DEC-N1",
        "type: decision",
        "status: approved",
        "approved_by: takeuchi",
        "question: 条件を書けない判断をどう残すか",
        "decision: 判断と理由だけ残し、verdict には参加させない",
        "provenance:",
        "  - type: adr",
        "    ref: docs/specs/engineering-assets-v0.1.md",
        "applies_to:",
        "  paths: ['src/*']",
        "  keywords: []",
    ]
    if with_conditions:
        lines += [
            "conditions:",
            "  - id: C1",
            "    status: active",
            "    statement: src/a.ts がある",
            "    expectation: present",
            "    verifier:",
            "      type: file_exists",
            "      targets: ['src/a.ts']",
        ]
    else:
        lines.append("conditions: []")
    (d / "DEC-N1.yaml").write_text("\n".join(lines), encoding="utf-8")
    return d


def _tiny_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
    return repo


def test_condition_less_decision_does_not_produce_a_verdict(tmp_path):
    """Condition が無い判断は hold を出さない（EA-14）。

    ここが hold のままだと、メモを足すほど全体が止まり inherit が出なくなる。
    """
    store = AssetStore.load(_note_asset(tmp_path))
    result = run(store, Task(id="t", description="", diff=""), _tiny_repo(tmp_path))

    assert result.evaluation is None, "確かめようのない判断で verdict を出さないこと"
    assert result.reference_decisions == ["DEC-N1"]


def test_condition_less_decision_still_reaches_the_briefing(tmp_path):
    """verdict には入らないが、知識としては必ず手渡されること。"""
    assets = _note_asset(tmp_path)
    store = AssetStore.load(assets)
    result = run(store, Task(id="t", description="", diff=""), _tiny_repo(tmp_path))

    b = briefing_mod.build(store, result, _tiny_repo(tmp_path))
    assert [r["id"] for r in b.references] == ["DEC-N1"]
    text = briefing_mod.to_prompt(b)
    assert "参照メモ" in text
    assert "verdict には参加させない" in text


def test_verifiable_decision_is_unaffected(tmp_path):
    """Condition を持つ判断は従来どおり verdict を出す（回帰）。"""
    store = AssetStore.load(_note_asset(tmp_path, with_conditions=True))
    result = run(store, Task(id="t", description="", diff=""), _tiny_repo(tmp_path))

    assert result.evaluation is not None
    assert result.evaluation.verdict == "inherit"
    assert result.reference_decisions == []


def test_approve_changes_only_status_and_approver(tmp_path):
    """承認は status と approved_by の 2 行だけを変える。本文に触らない。"""
    d = _note_asset(tmp_path)
    path = d / "DEC-N1.yaml"
    path.write_text(
        path.read_text(encoding="utf-8")
        .replace("status: approved", "status: candidate")
        .replace("approved_by: takeuchi", "approved_by: unapproved"),
        encoding="utf-8",
    )
    original_body = [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if not ln.startswith(("status:", "approved_by:"))
    ]

    msg = approve.apply(approve.find(d, "DEC-N1"), by="takeuchi")

    text = path.read_text(encoding="utf-8")
    assert "status: approved" in text
    assert "approved_by: takeuchi" in text
    assert "candidate" in msg and "approved" in msg
    body_now = [ln for ln in text.splitlines() if not ln.startswith(("status:", "approved_by:"))]
    assert body_now == original_body, "本文は1文字も変えないこと"


def test_approve_refuses_placeholder_and_missing_provenance(tmp_path):
    """穴が残った候補を承認できないこと（EA-10 / 穴あき資産の流入を防ぐ）。"""
    d = _note_asset(tmp_path)
    path = d / "DEC-N1.yaml"

    # [要記述] が残っている
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "decision: 判断と理由だけ残し、verdict には参加させない",
            "decision: [要記述]",
        ).replace("status: approved", "status: candidate"),
        encoding="utf-8",
    )
    with pytest.raises(approve.ApproveError, match="要記述"):
        approve.apply(path, by="takeuchi")

    # provenance が無い
    text = path.read_text(encoding="utf-8").replace("decision: [要記述]", "decision: 何か")
    text = "\n".join(
        ln for ln in text.splitlines()
        if not ln.startswith("provenance:") and not ln.strip().startswith(("- type: adr", "ref: docs/"))
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(approve.ApproveError, match="provenance"):
        approve.apply(path, by="takeuchi")
