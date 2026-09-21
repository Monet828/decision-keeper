"""差分に含まれるテスト無効化の検出（R-10）。

テスト削除・skip/only の付与・アサーション削除を、
「前提が維持された証拠」として扱ってはならない。
検出したら前提判定より前に指摘し、継承判定を出さない。
ignight の src/domain/policy/test-shape.ts と同じ役割。
"""

from __future__ import annotations

import re

from .models import GuardFinding

TEST_FILE = re.compile(
    r"(^|/)(tests?/|test_|.*_test\.|.*\.test\.|.*\.spec\.)", re.IGNORECASE
)
ASSERTION = re.compile(r"\b(assert|expect|should)\b")

ADDED_DISABLE = [
    (
        "test_skipped",
        re.compile(r"(\.skip\b|@pytest\.mark\.skip|@unittest\.skip|xit\(|xdescribe\()"),
    ),
    ("test_only", re.compile(r"(\.only\b|\bfit\(|\bfdescribe\()")),
]


def scan_diff(diff_text: str) -> list[GuardFinding]:
    """unified diff を走査し、検査を弱める変更を列挙する。"""
    findings: list[GuardFinding] = []
    current = ""
    new_lineno = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            if current.startswith("b/"):
                current = current[2:]
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            new_lineno = int(m.group(1)) if m else 0
            continue
        if line.startswith("---") or line.startswith("diff ") or line.startswith("index "):
            continue

        is_add = line.startswith("+")
        is_del = line.startswith("-")
        body = line[1:] if (is_add or is_del) else line

        if is_add:
            for kind, pat in ADDED_DISABLE:
                if pat.search(body):
                    findings.append(
                        GuardFinding(kind=kind, path=current, line=new_lineno,
                                     excerpt=body.strip()[:200])
                    )
            new_lineno += 1
        elif is_del:
            if TEST_FILE.search(current):
                if re.search(r"\b(def test_|it\(|test\(|describe\()", body):
                    findings.append(
                        GuardFinding(kind="test_deleted", path=current, line=new_lineno,
                                     excerpt=body.strip()[:200])
                    )
                elif ASSERTION.search(body):
                    findings.append(
                        GuardFinding(kind="assertion_removed", path=current, line=new_lineno,
                                     excerpt=body.strip()[:200])
                    )
        else:
            new_lineno += 1

    return findings
