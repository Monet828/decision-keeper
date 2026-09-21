"""決定論的な証拠コレクタ（R-02）。

LLMは一切関与しない。observed facts のみを返す。
証拠0件は「0件」として返し、欠測と混同しない。
ignight の log-extract.ts に倣い、抜き出す行は上限で切る。
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

from ..models import Assumption, AssumptionEvidence, Evidence

MAX_HITS = 50
MAX_EXCERPT_CHARS = 200
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


def _iter_files(repo: Path, patterns: list[str]):
    """glob パターンに一致する追跡対象ファイルを列挙する。"""
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(repo).as_posix()
        if not patterns or any(fnmatch.fnmatch(rel, pat) for pat in patterns):
            yield path, rel


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def collect_grep(repo: Path, assumption: Assumption) -> AssumptionEvidence:
    """正規表現で本文を検索する。"""
    v = assumption.verify
    pattern = re.compile(v.pattern or "", re.IGNORECASE)
    hits: list[Evidence] = []
    scanned = 0

    for path, rel in _iter_files(repo, v.paths):
        scanned += 1
        for lineno, line in enumerate(_read_lines(path), start=1):
            if len(hits) >= MAX_HITS:
                break
            if pattern.search(line):
                hits.append(
                    Evidence(
                        collector="grep",
                        path=rel,
                        line=lineno,
                        excerpt=line.strip()[:MAX_EXCERPT_CHARS],
                    )
                )

    found = bool(hits)
    note = (
        f"{scanned} ファイルを走査し、パターン /{v.pattern}/ に一致する行を "
        f"{len(hits)} 件検出した。"
    )
    if len(hits) >= MAX_HITS:
        note += f" 表示は上限 {MAX_HITS} 件で打ち切っている。"

    return AssumptionEvidence(
        assumption_id=assumption.id,
        statement=assumption.statement,
        expect=v.expect,
        scanned_files=scanned,
        evidence=hits,
        expectation_met=(found if v.expect == "present" else not found),
        collector_note=note,
    )


def collect_file_exists(repo: Path, assumption: Assumption) -> AssumptionEvidence:
    """パターンに一致するファイルの存在を確認する。"""
    v = assumption.verify
    hits = [
        Evidence(collector="file_exists", path=rel, excerpt="(ファイルが存在する)")
        for _, rel in _iter_files(repo, v.paths)
    ][:MAX_HITS]

    found = bool(hits)
    return AssumptionEvidence(
        assumption_id=assumption.id,
        statement=assumption.statement,
        expect=v.expect,
        scanned_files=len(hits),
        evidence=hits,
        expectation_met=(found if v.expect == "present" else not found),
        collector_note=(
            f"パターン {v.paths} に一致するファイルを {len(hits)} 件検出した。"
        ),
    )


# テスト無効化の検出パターン（R-10 とコレクタの両方で使う）
DISABLE_PATTERNS: list[tuple[str, str]] = [
    ("test_skipped", r"(?:\.skip\b|@pytest\.mark\.skip|@unittest\.skip|xit\(|xdescribe\()"),
    ("test_only", r"(?:\.only\b|fit\(|fdescribe\()"),
]


def collect_ast_test_shape(repo: Path, assumption: Assumption) -> AssumptionEvidence:
    """テストの無効化（skip / only）の有無を調べる。

    設計案では TypeScript AST を挙げたが、合成リポジトリが Python のため
    まず正規表現で実装した。限界はレポートに明記する。
    """
    v = assumption.verify
    hits: list[Evidence] = []
    scanned = 0

    for path, rel in _iter_files(repo, v.paths):
        scanned += 1
        for lineno, line in enumerate(_read_lines(path), start=1):
            for _kind, pat in DISABLE_PATTERNS:
                if re.search(pat, line):
                    hits.append(
                        Evidence(
                            collector="ast_test_shape",
                            path=rel,
                            line=lineno,
                            excerpt=line.strip()[:MAX_EXCERPT_CHARS],
                        )
                    )
                    break

    found = bool(hits)
    return AssumptionEvidence(
        assumption_id=assumption.id,
        statement=assumption.statement,
        expect=v.expect,
        scanned_files=scanned,
        evidence=hits[:MAX_HITS],
        expectation_met=(found if v.expect == "present" else not found),
        collector_note=(
            f"{scanned} ファイルを走査し、無効化マーカーを {len(hits)} 件検出した。"
            " 検出は正規表現によるもので、AST解析ではない。"
        ),
    )


def collect_run_tests(repo: Path, assumption: Assumption) -> AssumptionEvidence:
    """リポジトリ内でテストを実行し、成否を証拠にする。"""
    v = assumption.verify
    cmd = v.pattern or "python3 -m pytest -q"
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=repo, capture_output=True, text=True, timeout=120
        )
        passed = proc.returncode == 0
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
        excerpt = " / ".join(line.strip() for line in tail)[:MAX_EXCERPT_CHARS]
        note = f"`{cmd}` を実行し、終了コード {proc.returncode} を得た。"
    except (subprocess.TimeoutExpired, OSError) as exc:
        passed = False
        excerpt = f"実行できなかった: {exc}"
        note = f"`{cmd}` を実行できなかった。成功扱いにはしない。"

    hits = [Evidence(collector="run_tests", path=cmd, excerpt=excerpt)] if passed else []
    return AssumptionEvidence(
        assumption_id=assumption.id,
        statement=assumption.statement,
        expect=v.expect,
        scanned_files=1,
        evidence=hits,
        expectation_met=(passed if v.expect == "present" else not passed),
        collector_note=note,
    )


COLLECTORS = {
    "grep": collect_grep,
    "file_exists": collect_file_exists,
    "ast_test_shape": collect_ast_test_shape,
    "run_tests": collect_run_tests,
}


def collect_all(repo: Path, assumptions: list[Assumption]) -> list[AssumptionEvidence]:
    """すべての前提について証拠を集める（R-02）。"""
    return [COLLECTORS[a.verify.method](repo, a) for a in assumptions]
