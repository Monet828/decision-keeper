"""Verifier の実行と Evidence の生成（原典§4, §6）。

ここは Observation だけを作る。judgment は一切付けない（EA-04）。
「探索して0件」と「探索していない」を別の Evidence 型で返す（EA-06）。
"""

from __future__ import annotations

import fnmatch
import itertools
import re
import subprocess
from pathlib import Path

from .schema import Condition, Evidence

MAX_SAMPLES = 20
MAX_EXCERPT = 200
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".orca"}

_counter = itertools.count(1)


def _new_id() -> str:
    return f"EV-{next(_counter):04d}"


def _split_targets(patterns: list[str]) -> tuple[list[str], list[str]]:
    """対象を「このリポジトリ内」と「外部（絶対パス）」に分ける。

    Condition が別リポジトリの状態を問うことがある（移植元が実在するか等）。
    絶対パスまたは ~ 始まりの target は、root ではなくそのパス自身を見る。
    """
    inside = [p for p in patterns if not (p.startswith("/") or p.startswith("~"))]
    outside = [p for p in patterns if p.startswith("/") or p.startswith("~")]
    return inside, outside


def _iter_external(patterns: list[str]):
    """絶対パスの glob を直接展開する。"""
    import glob as _glob

    for pat in patterns:
        expanded = str(Path(pat).expanduser())
        for hit in sorted(_glob.glob(expanded, recursive=True)):
            path = Path(hit)
            if path.is_file() and not any(p in SKIP_DIRS for p in path.parts):
                yield path, hit


def _iter_files(root: Path, patterns: list[str]):
    inside, outside = _split_targets(patterns)
    yield from _iter_external(outside)

    if not root.is_dir():
        return
    # 外部だけを指定した場合は、このリポジトリ内は走査しない
    if outside and not inside:
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if not inside or any(fnmatch.fnmatch(rel, pat) for pat in inside):
            yield path, rel


def _lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _not_observed(condition: Condition, why: str) -> Evidence:
    """観測できなかったことを記録する。0件とは別物（EA-06）。"""
    return Evidence(
        id=_new_id(),
        type="not_observed",
        observation={"observed": False, "reason": why},
        query={"verifier": condition.verifier.type, "targets": condition.verifier.targets},
    )


def _grep(root: Path, condition: Condition) -> Evidence:
    v = condition.verifier
    if not v.patterns:
        return _not_observed(condition, "patterns が指定されていない")

    rx = re.compile("|".join(v.patterns), re.IGNORECASE)
    scanned = 0
    samples: list[dict] = []
    matches = 0
    for path, rel in _iter_files(root, v.targets):
        scanned += 1
        for lineno, line in enumerate(_lines(path), start=1):
            if rx.search(line):
                matches += 1
                if len(samples) < MAX_SAMPLES:
                    samples.append(
                        {"path": rel, "line": lineno, "excerpt": line.strip()[:MAX_EXCERPT]}
                    )

    if scanned == 0:
        return _not_observed(condition, f"対象 {v.targets} に該当するファイルが無い")

    return Evidence(
        id=_new_id(),
        type="grep_result",
        observation={"files_scanned": scanned, "matches": matches},
        query={"patterns": v.patterns, "targets": v.targets},
        samples=samples,
    )


def _file_exists(root: Path, condition: Condition) -> Evidence:
    v = condition.verifier
    if not v.targets:
        return _not_observed(condition, "targets が指定されていない")
    inside, outside = _split_targets(v.targets)
    # リポジトリ内の target を問うのに root が無ければ、探索そのものが成立していない。
    if inside and not root.is_dir():
        return _not_observed(condition, f"対象リポジトリ {root} が見つからない")
    hits = [rel for _, rel in _iter_files(root, v.targets)]
    # files_scanned に一致件数を入れてはならない。入れると「ファイルが存在しない」が
    # 「探索していない」と同じ形（scanned=0）になり、expectation: absent の Condition が
    # 原理的に supported へ到達できなくなる（EA-06 の「探索して0件」≠「探索していない」に反する）。
    # 実測: DEC-004 C1（vercel.json が無いこと）が not_observed になり、判定が hold に落ちた。
    # file_exists の探索単位は target なので、確認した target 数を scanned とする。
    return Evidence(
        id=_new_id(),
        type="file_list",
        observation={"files_scanned": len(v.targets), "matches": len(hits)},
        query={"targets": v.targets},
        samples=[{"path": r} for r in hits[:MAX_SAMPLES]],
    )


def _dependency_version(root: Path, condition: Condition) -> Evidence:
    """依存の宣言を探す。pyproject.toml / package.json / requirements.txt。"""
    v = condition.verifier
    names = v.patterns or []
    if not names:
        return _not_observed(condition, "patterns（依存名）が指定されていない")

    files = ["pyproject.toml", "package.json", "requirements.txt"]
    found: list[dict] = []
    scanned = 0
    for fname in files:
        path = root / fname
        if not path.exists():
            continue
        scanned += 1
        for lineno, line in enumerate(_lines(path), start=1):
            for name in names:
                if name.lower() in line.lower():
                    found.append(
                        {"path": fname, "line": lineno, "excerpt": line.strip()[:MAX_EXCERPT]}
                    )
    if scanned == 0:
        return _not_observed(condition, "依存を宣言するファイルが見つからない")
    return Evidence(
        id=_new_id(),
        type="dependency_version",
        observation={"files_scanned": scanned, "matches": len(found)},
        query={"dependencies": names},
        samples=found[:MAX_SAMPLES],
    )


def _config_value(root: Path, condition: Condition) -> Evidence:
    """設定ファイル内の値を探す。grep との違いは対象が設定に限られること。"""
    v = condition.verifier
    targets = v.targets or ["*.toml", "*.yaml", "*.yml", "*.json", "*.ini", "*.cfg", "*.env*"]
    sub = Condition(
        id=condition.id, statement=condition.statement, expectation=condition.expectation,
        verifier=v.model_copy(update={"targets": targets}),
    )
    ev = _grep(root, sub)
    if ev.type == "grep_result":
        ev.type = "config_value"
    return ev


def _test(root: Path, condition: Condition) -> Evidence:
    """テストを実行し、終了コードを観測する。成否の解釈はここでしない。"""
    v = condition.verifier
    cmd = v.patterns[0] if v.patterns else "python3 -m pytest -q"
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=180
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return _not_observed(condition, f"テストを実行できなかった: {type(exc).__name__}")

    tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
    return Evidence(
        id=_new_id(),
        type="test_result",
        observation={"exit_code": proc.returncode, "passed": proc.returncode == 0},
        query={"command": cmd},
        source={"cwd": str(root)},
        samples=[{"excerpt": line.strip()[:MAX_EXCERPT]} for line in tail],
    )


def _manual(root: Path, condition: Condition) -> Evidence:
    """human / document_search は自動では確認できない（原典§5）。"""
    return _not_observed(
        condition,
        f"verifier.type={condition.verifier.type} は自動確認できない。人の確認が必要",
    )


VERIFIERS = {
    "grep": _grep,
    "file_exists": _file_exists,
    "config_value": _config_value,
    "dependency_version": _dependency_version,
    "test": _test,
    "document_search": _manual,
    "human": _manual,
}


def run(root: Path, condition: Condition) -> Evidence:
    """Condition の verifier を実行して Evidence を1件返す。"""
    return VERIFIERS[condition.verifier.type](root, condition)
