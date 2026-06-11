from __future__ import annotations

import os
from typing import Any

try:
    import requests
except ImportError as exc:
    raise ImportError("缺少依赖，请运行: pip install requests") from exc


def is_local_dev() -> bool:
    host = os.environ.get("APP_HOST", "127.0.0.1").strip()
    return host not in {"0.0.0.0", "::"}


def remote_base() -> str:
    if not is_local_dev():
        return ""
    if os.environ.get("DISABLE_REMOTE_PROXY", "").lower() in {"1", "true", "yes"}:
        return ""

    base = os.environ.get("REMOTE_API_BASE", "").strip().rstrip("/")
    if base:
        return base

    public = os.environ.get("PUBLIC_HOST", "8.137.177.25").strip().rstrip("/")
    if not public:
        return ""
    if public.startswith("http://") or public.startswith("https://"):
        return public if public.endswith("/listing") else f"{public}/listing"
    return f"http://{public}/listing"


def is_whitelist_error(exc: Exception) -> bool:
    hint = str(exc)
    return "403" in hint or "白名单" in hint or "Forbidden" in hint


def annotate_proxy(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("source") != "lingxing":
        return result
    message = str(result.get("message") or "数据来源：领星 API")
    if "代理" not in message:
        result = dict(result)
        result["message"] = f"{message}（本地经阿里云代理）"
    return result


def remote_get(path: str, params: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any] | None:
    base = remote_base()
    if not base:
        return None
    url = f"{base}{path}"
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        return annotate_proxy(payload) if isinstance(payload, dict) else None
    except Exception as exc:
        print(f"[proxy] GET {url} failed: {exc}")
        return None


def remote_post(path: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any] | None:
    base = remote_base()
    if not base:
        return None
    url = f"{base}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        print(f"[proxy] POST {url} failed: {exc}")
        return None
