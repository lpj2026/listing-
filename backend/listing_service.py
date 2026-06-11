from __future__ import annotations

from typing import Any

from lingxing_client import LingxingClient
from lingxing_utils import api_error, extract_list, is_ok_code
from remote_proxy import is_whitelist_error, remote_post


def _require_client() -> LingxingClient:
    client = LingxingClient.from_env()
    if client is None:
        raise RuntimeError("未配置 LINGXING_APP_ID / LINGXING_APP_SECRET")
    return client


def find_listing_by_msku(
    store_id: int,
    msku: str,
    *,
    page_size: int = 50,
    max_pages: int = 20,
) -> dict[str, Any] | None:
    try:
        client = _require_client()
        target = msku.strip()
        if not store_id or not target:
            return None

        for page in range(max_pages):
            offset = page * page_size
            response = client.request(
                "POST",
                "/erp/sc/data/mws/listing",
                {
                    "sid": store_id,
                    "is_pair": 2,
                    "offset": offset,
                    "length": page_size,
                },
            )
            if not is_ok_code(response.get("code")):
                raise RuntimeError(api_error(response, "Listing 查询失败"))

            items = extract_list(response)
            for item in items:
                seller_sku = str(item.get("seller_sku") or item.get("msku") or "").strip()
                if seller_sku == target:
                    return item

            if len(items) < page_size:
                break

        return None
    except Exception as exc:
        if not is_whitelist_error(exc):
            raise
        proxied = remote_post("/api/proxy/listing/find", {"store_id": store_id, "msku": msku})
        if proxied and proxied.get("code") == 1:
            return proxied.get("data")
        raise RuntimeError(f"Listing 查询失败：{exc}") from exc
