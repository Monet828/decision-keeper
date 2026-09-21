"""判断資産の読み込みと不変性の検証（R-05）。

判断資産は読み取り専用。人間の承認なしに更新しない（START-HERE.md の停止条件）。
読み込み時に SHA-256 を記録し、終了時に再計算して差異を検出する。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import DecisionAsset


class AssetError(Exception):
    """資産の読み込み・検証に失敗した。"""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_assets(assets_dir: Path) -> tuple[list[DecisionAsset], dict[str, str]]:
    """資産ディレクトリを読み込み、資産一覧と (パス -> SHA-256) を返す（R-05）。"""
    if not assets_dir.is_dir():
        raise AssetError(f"資産ディレクトリが見つかりません: {assets_dir}")

    assets: list[DecisionAsset] = []
    digests: dict[str, str] = {}

    for path in sorted(assets_dir.rglob("*.yaml")) + sorted(assets_dir.rglob("*.yml")):
        digests[str(path)] = _digest(path)
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise AssetError(f"YAMLとして読めません: {path}: {exc}") from exc
        if raw is None:
            continue
        try:
            assets.append(DecisionAsset.model_validate(raw))
        except ValidationError as exc:
            raise AssetError(f"判断資産のスキーマに合いません: {path}\n{exc}") from exc

    if not assets:
        raise AssetError(f"判断資産が1件もありません: {assets_dir}")
    return assets, digests


def verify_unchanged(digests: dict[str, str]) -> tuple[bool, list[str]]:
    """読み込み時のSHA-256と現在を比較する（R-05）。

    戻り値: (すべて不変か, 変化したパスの一覧)
    """
    changed: list[str] = []
    for path_str, expected in digests.items():
        path = Path(path_str)
        if not path.exists():
            changed.append(f"{path_str} (削除された)")
            continue
        if _digest(path) != expected:
            changed.append(path_str)
    return (not changed), changed
