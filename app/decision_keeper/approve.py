"""候補資産を承認する（EA-14）。

承認は「YAML を開いて status を書き換える」手作業だった。候補が溜まる一方に
なる原因なので、1 コマンドにする。

変えるのは status と approved_by の 2 つだけ。本文には触らない。
"""

from __future__ import annotations

import re
from pathlib import Path

VALID = {"approved", "deprecated", "superseded"}


class ApproveError(Exception):
    pass


def find(assets_dir: Path, asset_id: str) -> Path:
    for path in sorted(assets_dir.rglob("*.yaml")) + sorted(assets_dir.rglob("*.yml")):
        if re.search(rf"^id:\s*{re.escape(asset_id)}\s*$", path.read_text(encoding="utf-8"), re.M):
            return path
    raise ApproveError(f"見つかりません: {asset_id}")


def apply(path: Path, by: str, status: str = "approved") -> str:
    if status not in VALID:
        raise ApproveError(f"status は {'/'.join(sorted(VALID))} のいずれか: {status}")
    if not by.strip():
        raise ApproveError("承認者名（--by）が必要（EA-10: 出どころをたどれること）")

    text = path.read_text(encoding="utf-8")
    before = re.search(r"^status:\s*(\S+)\s*$", text, re.M)
    if before is None:
        raise ApproveError(f"status 行がありません: {path}")
    if before.group(1) == status:
        raise ApproveError(f"既に status={status} です: {path.name}")

    # provenance が無い Asset は approved にできない（EA-10）。
    if status == "approved" and not re.search(r"^provenance:\s*$", text, re.M):
        raise ApproveError(f"provenance が無いので approved にできません（EA-10）: {path.name}")

    # [要記述] が残ったまま承認すると、穴あきの資産が検索に出てしまう。
    if status == "approved" and "[要記述]" in text:
        raise ApproveError(f"[要記述] が残っています。埋めてから承認してください: {path.name}")

    text = re.sub(r"^status:\s*\S+\s*$", f"status: {status}", text, count=1, flags=re.M)
    if re.search(r"^approved_by:\s*.*$", text, re.M):
        text = re.sub(r"^approved_by:\s*.*$", f"approved_by: {by}", text, count=1, flags=re.M)
    else:
        text = re.sub(r"^status: .*$", f"status: {status}\napproved_by: {by}", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8")
    return f"{path.name}: status {before.group(1)} → {status}（承認者 {by}）"
