from __future__ import annotations

from typing import Any


def is_ok_code(code: Any) -> bool:
    return str(code) in {"0", "1", "200"}


def api_error(payload: dict[str, Any], default: str = "领星接口失败") -> str:
    return str(payload.get("msg") or payload.get("message") or default)


def extract_list(payload: dict[str, Any]) -> list[Any]:
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested = data.get("data")
        if isinstance(nested, list):
            return nested
    return []
