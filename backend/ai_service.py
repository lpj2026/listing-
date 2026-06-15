"""AI service — DeepSeek (OpenAI-compatible) client."""
from __future__ import annotations

import json
import os
import re
from typing import Any

try:
    import requests
except ImportError as exc:
    raise ImportError("缺少依赖，请运行: pip install requests") from exc

DEEPSEEK_BASE = os.environ.get("AI_API_BASE", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_KEY = os.environ.get("AI_API_KEY", "").strip()
DEEPSEEK_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.environ.get("AI_TIMEOUT", "90"))


def _chat(messages: list[dict], *, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    if not DEEPSEEK_KEY:
        raise RuntimeError("未配置 AI_API_KEY，请在 .env 中设置")
    url = f"{DEEPSEEK_BASE}/chat/completions"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json={"model": DEEPSEEK_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
        timeout=DEEPSEEK_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"AI API {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("AI 返回空内容")
    return content.strip()


def extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise RuntimeError(f"AI 返回无法解析为 JSON: {text[:300]}")
