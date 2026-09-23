"""Asset の読み込み、lifecycle、relation（原典§11, §14）。

Akibako 相当の最小版。Asset の現在有効性はここでは断定しない（原典§1）。
- candidate は通常検索で返さない（EA-02）
- approved は読み込み時にSHA-256を記録し、書き換えを検出する（EA-03）
"""

from __future__ import annotations

import fnmatch
import hashlib
from pathlib import Path

import yaml
from pydantic import ValidationError

from .schema import AssetRelation, DecisionAsset, ImplementationAsset

Asset = DecisionAsset | ImplementationAsset

# 通常検索で返す状態（原典§11）
SEARCHABLE: set[str] = {"approved"}


class StoreError(Exception):
    pass


class AssetStore:
    def __init__(self) -> None:
        self.decisions: dict[str, DecisionAsset] = {}
        self.implementations: dict[str, ImplementationAsset] = {}
        self.digests: dict[str, str] = {}
        self.skipped: list[str] = []

    # --- 読み込み ---

    @classmethod
    def load(cls, root: Path, include_candidates: bool = False) -> AssetStore:
        if not root.is_dir():
            raise StoreError(f"Asset ディレクトリが見つかりません: {root}")

        store = cls()
        paths = sorted(root.rglob("*.yaml")) + sorted(root.rglob("*.yml"))
        for path in paths:
            store.digests[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                raise StoreError(f"YAMLとして読めません: {path}: {exc}") from exc
            if not raw:
                continue

            kind = raw.get("type")
            asset_class = {"decision": DecisionAsset, "implementation": ImplementationAsset}.get(
                kind
            )
            if asset_class is None:
                raise StoreError(f"type が decision / implementation ではありません: {path}")
            try:
                asset = asset_class.model_validate(raw)
            except ValidationError as exc:
                raise StoreError(f"Asset のスキーマに合いません: {path}\n{exc}") from exc

            if not include_candidates and asset.status not in SEARCHABLE:
                store.skipped.append(f"{asset.id} (status={asset.status})")
                continue

            if isinstance(asset, DecisionAsset):
                store.decisions[asset.id] = asset
            else:
                store.implementations[asset.id] = asset
        return store

    def verify_unchanged(self) -> tuple[bool, list[str]]:
        """読み込み時のSHA-256と現在を比較する（EA-03）。"""
        changed: list[str] = []
        for path_str, expected in self.digests.items():
            path = Path(path_str)
            if not path.exists():
                changed.append(f"{path_str} (削除された)")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                changed.append(path_str)
        return (not changed), changed

    # --- 検索（原典§15） ---

    def search_decisions(
        self, changed_paths: list[str], text: str, repo_paths: list[str] | None = None
    ) -> list[tuple[DecisionAsset, str]]:
        return _match(self.decisions.values(), changed_paths, text, repo_paths)

    def search_implementations(
        self, changed_paths: list[str], text: str, repo_paths: list[str] | None = None
    ) -> list[tuple[ImplementationAsset, str]]:
        return _match(self.implementations.values(), changed_paths, text, repo_paths)

    # --- relation（原典§14） ---

    def related(self, asset_id: str) -> list[tuple[AssetRelation, Asset | None]]:
        """関連 Asset を返す。相手が存在しない場合も None として返す（片方だけを許容）。"""
        asset = self.decisions.get(asset_id) or self.implementations.get(asset_id)
        if asset is None:
            return []
        out: list[tuple[AssetRelation, Asset | None]] = []
        for rel in asset.related_assets:
            other = self.decisions.get(rel.id) or self.implementations.get(rel.id)
            out.append((rel, other))
        return out

    def decisions_for_implementation(self, impl_id: str) -> list[DecisionAsset]:
        """実装資産に紐づく判断資産（原典§14）。"""
        out = [
            self.decisions[rel.id]
            for rel, _ in self.related(impl_id)
            if rel.relationship == "implements" and rel.id in self.decisions
        ]
        # 逆向きの宣言しかない場合も拾う
        for dec in self.decisions.values():
            if any(
                r.id == impl_id and r.relationship == "implemented_by" for r in dec.related_assets
            ) and dec not in out:
                out.append(dec)
        return out


def _match(assets, changed_paths: list[str], text: str, repo_paths: list[str] | None = None):
    """Asset を検索する（原典§15 / EA-13）。

    差分があるときは変更パスだけを見る。差分が無いとき(着手時・検証専用の run)に限り、
    applies_to.paths を **リポジトリに実在するファイル** と照合する。

    差分がある回にまで範囲照合を足さないのは、広い applies_to.paths を持つ Asset が
    あらゆる変更に当たってしまうため。差分があるなら変更パスのほうが鋭い信号である。
    """
    low = text.lower()
    scope_basis = repo_paths if (not changed_paths and repo_paths) else None
    out = []
    for asset in assets:
        path_hits = [
            f"{p} が {pat} に一致"
            for pat in asset.applies_to.paths
            for p in changed_paths
            if fnmatch.fnmatch(p, pat)
        ]
        scope_hits: list[str] = []
        if scope_basis is not None:
            for pat in asset.applies_to.paths:
                found = [p for p in scope_basis if fnmatch.fnmatch(p, pat)]
                if found:
                    scope_hits.append(f"{pat} に {len(found)} 件")
        kw_hits = [kw for kw in asset.applies_to.keywords if kw.lower() in low]
        if not path_hits and not scope_hits and not kw_hits:
            continue
        parts = []
        if path_hits:
            parts.append("変更パスの一致: " + "、".join(path_hits[:5]))
        if scope_hits:
            parts.append("適用範囲がリポジトリに存在: " + "、".join(scope_hits[:5]))
        if kw_hits:
            parts.append("キーワードの一致: " + "、".join(kw_hits[:5]))
        out.append((asset, f"{asset.id} を選択した。" + " / ".join(parts)))
    return out
