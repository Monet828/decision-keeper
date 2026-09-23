"""変更提案に関連する判断資産の選択（R-01）。

applies_to のパスとキーワードで決定論的に照合し、選定理由を文字列で返す。
"""

from __future__ import annotations

import fnmatch
import re

from .models import DecisionAsset

DIFF_PATH = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def changed_paths(diff_text: str) -> list[str]:
    """差分から変更されたファイルパスを取り出す。"""
    return sorted({p.strip() for p in DIFF_PATH.findall(diff_text) if p.strip() != "/dev/null"})


def select(
    assets: list[DecisionAsset],
    diff_text: str,
    proposal_text: str,
    repo_paths: list[str] | None = None,
) -> list[tuple[DecisionAsset, str]]:
    """関連する資産と、その選定理由を返す（R-01 / EA-13）。

    差分があるときは変更パスだけを見る。差分が無いときに限り、applies_to.paths を
    **リポジトリに実在するファイル** と照合する（EA-13。v2 の _match と同じ規則）。
    """
    paths = changed_paths(diff_text)
    haystack = f"{proposal_text}\n{diff_text}".lower()
    scope_basis = repo_paths if (not paths and repo_paths) else None
    selected: list[tuple[DecisionAsset, str]] = []

    for asset in assets:
        path_hits = [
            f"{p} が {pat} に一致"
            for pat in asset.applies_to.paths
            for p in paths
            if fnmatch.fnmatch(p, pat)
        ]
        scope_hits: list[str] = []
        if scope_basis is not None:
            for pat in asset.applies_to.paths:
                found = [p for p in scope_basis if fnmatch.fnmatch(p, pat)]
                if found:
                    scope_hits.append(f"{pat} に {len(found)} 件")
        kw_hits = [kw for kw in asset.applies_to.keywords if kw.lower() in haystack]

        if not path_hits and not scope_hits and not kw_hits:
            continue

        reasons = []
        if path_hits:
            reasons.append("変更パスの一致: " + "、".join(path_hits[:5]))
        if scope_hits:
            reasons.append("適用範囲がリポジトリに存在: " + "、".join(scope_hits[:5]))
        if kw_hits:
            reasons.append("キーワードの一致: " + "、".join(kw_hits[:5]))
        selected.append((asset, f"{asset.id} を選択した。" + " / ".join(reasons)))

    return selected
