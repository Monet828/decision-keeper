"""LLMクライアント。差し替え可能なインターフェースにする。

APIキー未設定でも固定応答クライアントで全体が動く。
実呼び出し（OrcaRouter）と固定応答は、レポート上で必ず区別する（R-07）。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Protocol

DEFAULT_BASE_URL = "https://api.orcarouter.ai/v1"
DEFAULT_MODEL = "orcarouter/auto"
# 推論型モデルに振られると本文生成の前に推論トークンを消費し、応答が遅い。
# 実測では本番プロンプトで60秒を超えたため、既定を長くとる。
DEFAULT_TIMEOUT_SEC = 180.0


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_sec: float = 0.0
    is_stub: bool = False


class LLMClient(Protocol):
    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse: ...


class StubClient:
    """固定応答クライアント。

    LLMの判断力は再現しない。決定論的な expectation_met をそのまま写し、
    「証拠と提案文が食い違う」ケースだけ insufficient に倒す。
    これは配線とパイプラインを検証するためのものであり、
    判定品質の証拠にはならない。レポートには stub と明記される。
    """

    model = "stub/deterministic"

    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse:
        start = time.monotonic()
        start = user.find("<observations>")
        end = user.rfind("</observations>")
        payload = (
            json.loads(user[start + len("<observations>") : end])
            if start != -1 and end != -1
            else {}
        )
        judgements = []
        for item in payload.get("assumptions", []):
            if item.get("claimed_in_proposal") and item.get("expectation_met"):
                # 提案文は変化を主張するが、コードは資産の期待どおりのまま = 裏付けが無い
                status = "insufficient"
                reason = "提案文が主張する内容を裏付けるコード上の証拠が無い。"
            elif item["expectation_met"]:
                status, reason = "supported", "観測結果が資産の期待と一致した。"
            else:
                status, reason = "disputed", "観測結果が資産の期待と一致しない。"
            judgements.append(
                {"assumption_id": item["assumption_id"], "status": status, "reason": reason}
            )
        return LLMResponse(
            text=json.dumps({"judgements": judgements}, ensure_ascii=False),
            model=self.model,
            elapsed_sec=time.monotonic() - start,
            is_stub=True,
        )


class OrcaRouterClient:
    """OrcaRouter 経由の実呼び出し（OpenAI互換 /chat/completions）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ):
        self.api_key = api_key
        self.timeout_sec = timeout_sec
        self.base_url = (
            base_url or os.environ.get("ORCAROUTER_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.model = model or os.environ.get("ORCAROUTER_MODEL") or DEFAULT_MODEL

    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse:
        import httpx

        start = time.monotonic()
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=self.timeout_sec,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage") or {}
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            elapsed_sec=time.monotonic() - start,
            is_stub=False,
        )


def build_client(
    force_stub: bool = False, timeout_sec: float = DEFAULT_TIMEOUT_SEC
) -> LLMClient:
    """環境変数からクライアントを選ぶ。キーが無ければ固定応答に落とす。"""
    key = os.environ.get("ORCAROUTER_API_KEY", "").strip()
    if force_stub or not key:
        return StubClient()
    return OrcaRouterClient(api_key=key, timeout_sec=timeout_sec)
