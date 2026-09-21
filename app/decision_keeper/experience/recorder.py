"""orca-trace v0 互換の Experience レコーダ。

OrcaReplay が記録するのと同じ形式（JSONL + manifest + content-addressed blobs）で
開発中の出来事を書き出す。将来 `orca record` で取った本物のトレースも、
同じ Extractor で読めるようにするため、形式は仕様に合わせる。

出典: spec/orca-trace-v0.md (CC BY 4.0), packages/schema/schema/event.schema.json
確認日: 2026-09-21。schema_version 0.3.0 の manifest 形を参照した。

このレコーダは OrcaReplay 本体ではない。proxy による model.request/response の
捕捉は行わない。記録できるのは shell / fs / note の範囲に限られる。
その限界は manifest の adapter.id に明示する。
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "0.3.0"
ADAPTER_ID = "decision-keeper-shell"  # OrcaReplay 本体ではないことを明示する
MAX_INLINE_BYTES = 4096  # これを超える payload は blob へ退避（仕様の MUST）


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class Recorder:
    """1つの開発セッションを1つの run として記録する。"""

    def __init__(self, root: Path, run_id: str | None = None, cwd: Path | None = None):
        self.cwd = Path(cwd or Path.cwd())
        rid = run_id or hashlib.sha256(f"{time.time()}{self.cwd}".encode()).hexdigest()[:12]
        self.run_id = f"run_{rid}"
        self.dir = root / "runs" / self.run_id
        self.blobs = self.dir / "blobs"
        self.events_path = self.dir / "events.jsonl"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.blobs.mkdir(parents=True, exist_ok=True)

        self._seq = 0
        self._turn = 0
        self._t0 = time.monotonic()
        self._blob_count = 0
        self._started = _now_iso()

        self.emit("run.start", actor="orca", attrs={"adapter": ADAPTER_ID, "cwd": str(self.cwd)})

    @classmethod
    def resume(cls, run_dir: Path) -> Recorder:
        """既存の run に追記する。プロセスをまたいで記録を続けるため。

        seq と turn は events.jsonl の末尾から復元する。mono_us は
        プロセス起動時点を基準にするため、再開をまたぐと連続しない。
        その旨を note として残す。
        """
        self = cls.__new__(cls)
        self.dir = run_dir
        self.blobs = run_dir / "blobs"
        self.events_path = run_dir / "events.jsonl"
        self.run_id = run_dir.name
        self.blobs.mkdir(parents=True, exist_ok=True)

        last_seq, last_turn = -1, 0
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                last_seq = max(last_seq, int(ev.get("seq", -1)))
                last_turn = max(last_turn, int(ev.get("turn", 0)))

        manifest = run_dir / "manifest.json"
        meta = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
        self.cwd = Path(meta.get("cwd", Path.cwd()))
        self._seq = last_seq + 1
        self._turn = last_turn
        self._t0 = time.monotonic()
        self._blob_count = int((meta.get("counts") or {}).get("blobs", 0))
        self._started = meta.get("created_at", _now_iso())
        return self

    @classmethod
    def open_or_resume(cls, root: Path, run_id: str, cwd: Path | None = None) -> Recorder:
        run_dir = root / "runs" / run_id
        if (run_dir / "events.jsonl").exists():
            return cls.resume(run_dir)
        return cls(root, run_id=run_id.replace("run_", ""), cwd=cwd)

    # --- 低レベル ---

    def _store_blob(self, data: bytes, media_type: str) -> dict:
        digest = hashlib.sha256(data).hexdigest()
        sub = self.blobs / digest[:2]
        sub.mkdir(parents=True, exist_ok=True)
        path = sub / digest
        if not path.exists():
            path.write_bytes(data)
            self._blob_count += 1
        return {"$blob": f"sha256:{digest}", "bytes": len(data), "media_type": media_type}

    def emit(
        self,
        type_: str,
        actor: str = "agent",
        attrs: dict | None = None,
        payload: str | bytes | None = None,
        media_type: str = "text/plain",
        causes: list[int] | None = None,
    ) -> int:
        """1イベントを追記し、その seq を返す。"""
        event: dict = {
            "seq": self._seq,
            "ts": _now_iso(),
            "mono_us": int((time.monotonic() - self._t0) * 1_000_000),
            "turn": self._turn,
            "type": type_,
            "actor": actor,
        }
        if causes:
            event["causes"] = sorted(c for c in causes if c < self._seq)
        if attrs:
            event["attrs"] = attrs
        if payload is not None:
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            event["payload"] = (
                self._store_blob(data, media_type)
                if len(data) > MAX_INLINE_BYTES
                else {"text": data.decode("utf-8", errors="replace")}
            )

        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._seq += 1
        return event["seq"]

    def next_turn(self) -> int:
        self._turn += 1
        return self._turn

    # --- 高レベル ---

    def shell(self, argv: list[str], cwd: Path | None = None, causes: list[int] | None = None):
        """コマンドを実行し、shell.exec と shell.result を記録する。"""
        work = Path(cwd or self.cwd)
        exec_seq = self.emit(
            "shell.exec", actor="harness",
            attrs={"argv": argv, "cwd": str(work)}, causes=causes,
        )
        started = time.monotonic()
        try:
            proc = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=600)
            out, err, code = proc.stdout, proc.stderr, proc.returncode
        except (subprocess.TimeoutExpired, OSError) as exc:
            out, err, code = "", f"{type(exc).__name__}: {exc}", -1

        combined = (out + err).strip()
        self.emit(
            "shell.result", actor="harness",
            attrs={
                "exit_code": code,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "stdout_bytes": len(out.encode()),
                "stderr_bytes": len(err.encode()),
            },
            payload=combined or None,
            causes=[exec_seq],
        )
        return code, combined

    def fs_change(self, path: str, status: str, diff: str, causes: list[int] | None = None) -> int:
        """ファイル変更を記録する。差分は payload に入れる。"""
        lines = diff.splitlines()
        insertions = sum(1 for ln in lines if ln.startswith("+") and not ln.startswith("+++"))
        deletions = sum(1 for ln in lines if ln.startswith("-") and not ln.startswith("---"))
        return self.emit(
            "fs.change", actor="agent",
            attrs={"path": path, "status": status,
                   "insertions": insertions, "deletions": deletions},
            payload=diff, media_type="text/x-diff", causes=causes,
        )

    def target_repo(self, path: Path) -> int:
        """作業対象のリポジトリを明示する。

        manifest の cwd は CLI を起動した場所であり、作業対象とは限らない。
        実測: 別リポジトリを操作したとき、manifest.cwd が記録側を指してしまい
        実装資産の repository / commit を取り違えた。取り違えを防ぐため明示する。
        """
        info = _git_info(Path(path))
        return self.emit(
            "note", actor="orca",
            attrs={"kind": "target_repo", "path": str(path), **info},
            payload=f"作業対象リポジトリ: {path}",
        )

    def note(self, text: str, kind: str = "note", causes: list[int] | None = None) -> int:
        """人またはエージェントの覚書。理由はここにしか残らないことが多い。"""
        return self.emit("note", actor="agent", attrs={"kind": kind}, payload=text, causes=causes)

    def close(self, exit_code: int = 0) -> Path:
        self.emit("run.end", actor="orca", attrs={"exit_code": exit_code})
        events_bytes = self.events_path.read_bytes()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "created_at": self._started,
            "ended_at": _now_iso(),
            "orca_version": None,
            "adapter": {"id": ADAPTER_ID, "version": "0.1.0", "harness_version": None},
            "argv": ["decision-keeper", "record"],
            "cwd": str(self.cwd),
            "env_allowlisted": {
                k: os.environ.get(k, "") for k in ("TERM", "LANG") if k in os.environ
            },
            "git": _git_info(self.cwd),
            "platform": {"os": platform.system().lower(), "arch": platform.machine(),
                         "python": platform.python_version()},
            "counts": {"events": self._seq, "blobs": self._blob_count},
            "exit_code": exit_code,
            "integrity": {
                "events_sha256": hashlib.sha256(events_bytes).hexdigest(),
                "blob_count": self._blob_count,
            },
            "limitations": [
                "OrcaReplay 本体ではない。model.request / model.response は捕捉していない。",
                "記録できるのは shell / fs / note に限られる。",
            ],
        }
        path = self.dir / "manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.dir


def _git_info(cwd: Path) -> dict:
    def _run(args: list[str]) -> str | None:
        try:
            p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=10)
            return p.stdout.strip() if p.returncode == 0 else None
        except OSError:
            return None

    head = _run(["git", "rev-parse", "HEAD"])
    if head is None:
        return {"head": None, "branch": None, "dirty": None}
    return {
        "head": head,
        "branch": _run(["git", "branch", "--show-current"]),
        "dirty": bool(_run(["git", "status", "--porcelain"])),
    }
