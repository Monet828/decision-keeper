"""呼び出し回数・トークン・実行時間の上限と停止（R-08）。

上限に達したら新たな呼び出しを行わず、打ち切った旨を記録する。
既定値は ignight の DEFAULT_PROPOSE_LIMIT=1 / CHECK_TIMEOUT_MS=300_000 に倣う。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

DEFAULT_MAX_LLM_CALLS = 1
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TIMEOUT_SEC = 300


@dataclass
class Limits:
    max_llm_calls: int = DEFAULT_MAX_LLM_CALLS
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout_sec: int = DEFAULT_TIMEOUT_SEC

    started_at: float = field(default_factory=time.monotonic)
    llm_calls_used: int = 0
    hits: list[str] = field(default_factory=list)

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    def check_llm_call(self) -> bool:
        """LLM呼び出しを1回行ってよいか。不可なら理由を hits に記録する。"""
        if self.llm_calls_used >= self.max_llm_calls:
            self._record(
                f"LLM呼び出し上限に達したため打ち切り "
                f"(上限 {self.max_llm_calls} 回、実行 {self.llm_calls_used} 回)"
            )
            return False
        if self.elapsed() >= self.timeout_sec:
            self._record(
                f"実行時間の上限に達したため打ち切り "
                f"(上限 {self.timeout_sec} 秒、経過 {self.elapsed():.1f} 秒)"
            )
            return False
        return True

    def record_llm_call(self) -> None:
        self.llm_calls_used += 1

    def _record(self, message: str) -> None:
        if message not in self.hits:
            self.hits.append(message)
