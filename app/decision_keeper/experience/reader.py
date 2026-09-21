"""orca-trace v0 形式の Experience を読む。

自前レコーダの出力と、OrcaReplay 本体の出力の両方を同じ形で読む。
仕様が MUST として要求しているとおり、末尾が切れた行を許容し、
未知の type はスキップする（前方互換のため）。

出典: spec/orca-trace-v0.md（CC BY 4.0）確認日 2026-09-21
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field


class Event(BaseModel):
    seq: int
    ts: str = ""
    mono_us: int = 0
    turn: int = 0
    type: str
    actor: str = ""
    causes: list[int] = Field(default_factory=list)
    attrs: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)


class TraceReader:
    """読み取り専用。トレースを書き換えない。"""

    def __init__(self, root: Path):
        self.root = root
        self.manifest: dict = {}
        self.events: list[Event] = []
        self.problems: list[str] = []

    @classmethod
    def open(cls, root: Path) -> TraceReader:
        r = cls(root)
        manifest_path = root / "manifest.json"
        if manifest_path.exists():
            r.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            r.problems.append("manifest.json が無い")

        events_path = root / "events.jsonl"
        if not events_path.exists():
            r.problems.append("events.jsonl が無い")
            return r

        raw = events_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except ValueError:
                # 末尾が切れた行は許容する（仕様の MUST）
                r.problems.append(f"{lineno} 行目を JSON として読めなかった（切れている可能性）")
                continue
            try:
                r.events.append(Event.model_validate(data))
            except Exception:  # noqa: BLE001 - 未知の形はスキップする
                r.problems.append(f"{lineno} 行目のイベント形が想定外")
        return r

    def verify_integrity(self) -> tuple[bool, str]:
        """manifest の events_sha256 と実ファイルを突き合わせる。修復はしない。"""
        expected = (self.manifest.get("integrity") or {}).get("events_sha256")
        if not expected:
            return False, "manifest に integrity.events_sha256 が無い"
        actual = hashlib.sha256((self.root / "events.jsonl").read_bytes()).hexdigest()
        if actual != expected:
            return False, f"events.jsonl のハッシュが一致しない（期待 {expected[:12]}…）"
        return True, ""

    def payload_text(self, event: Event) -> str:
        """payload を取り出す。blob に退避されていれば読みに行く。"""
        p = event.payload or {}
        if "text" in p:
            return str(p["text"])
        ref = p.get("$blob", "")
        if ref.startswith("sha256:"):
            digest = ref.split(":", 1)[1]
            path = self.root / "blobs" / digest[:2] / digest
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")
            self.problems.append(f"blob が見つからない: {ref}")
        return ""

    def by_type(self, *types: str) -> list[Event]:
        wanted = set(types)
        return [e for e in self.events if e.type in wanted]

    def caused_by(self, seq: int) -> list[Event]:
        return [e for e in self.events if seq in e.causes]

    @property
    def adapter_id(self) -> str:
        return (self.manifest.get("adapter") or {}).get("id", "unknown")

    @property
    def run_id(self) -> str:
        return self.manifest.get("run_id", self.root.name)
