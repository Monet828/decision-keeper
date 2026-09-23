"""リポジトリに実在するファイルの一覧（EA-13）。

`applies_to.paths` を「変更されたファイル」ではなく「実在するファイル」と
照合するために使う。差分が無い Task（着手時・検証専用の run）で必要になる。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# 範囲照合は候補が多いほど緩くなる。上限を置いて、際限なく広がらないようにする。
MAX_REPO_PATHS = 20000

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}


def repo_paths(repo: Path) -> list[str]:
    """repo 直下からの相対パスを返す。git 管理下ならそれを使う。

    git を使うのは、生成物や無視対象を自然に外せるため。
    git が使えないときだけ走査へ落とす。
    """
    if not repo.is_dir():
        return []
    tracked = _git_tracked(repo)
    if tracked is not None:
        return tracked[:MAX_REPO_PATHS]
    return _walk(repo)[:MAX_REPO_PATHS]


def _git_tracked(repo: Path) -> list[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return sorted({ln.strip() for ln in proc.stdout.splitlines() if ln.strip()})


def _walk(repo: Path) -> list[str]:
    out: list[str] = []
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        out.append(p.relative_to(repo).as_posix())
        if len(out) >= MAX_REPO_PATHS:
            break
    return sorted(out)
