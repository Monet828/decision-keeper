"""モデル出力からJSONを取り出す。

プロバイダによって、生のJSON・コードフェンス付き・前後に地の文、と形が揃わない。
実測: OrcaRouter経由の deepseek は生JSON、anthropic/claude-sonnet-5 は
コードフェンスで囲んで返したためスキーマ検証に落ちた。

解釈できる形を広げるだけで、解釈できなければ失敗として扱う方針は変えない。
"""

from __future__ import annotations

import json
import re

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract(text: str) -> tuple[dict | None, str]:
    """(パースできた辞書 or None, 失敗理由) を返す。"""
    if not text or not text.strip():
        return None, "出力が空だった"

    candidates: list[str] = [text.strip()]

    m = FENCE.search(text)
    if m:
        candidates.append(m.group(1).strip())

    # 最外側の { ... } を括弧の対応で切り出す
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : i + 1])
                    break

    for cand in candidates:
        try:
            parsed = json.loads(cand)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed, ""

    return None, f"JSONとして読めなかった (先頭80字: {text.strip()[:80]!r})"
