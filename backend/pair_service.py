from __future__ import annotations

from typing import Any

from lingxing_client import LingxingClient
from lingxing_utils import api_error, is_ok_code
from remote_proxy import is_whitelist_error, remote_post


def _require_client() -> LingxingClient:
    client = LingxingClient.from_env()
    if client is None:
        raise RuntimeError("未配置 LINGXING_APP_ID / LINGXING_APP_SECRET")
    return client


def pair_msku_to_local_sku(
    *,
    seller_id: str,
    marketplace_id: str,
    msku: str,
    local_sku: str,
    is_sync_pic: int = 1,
) -> dict[str, Any]:
    seller_id = seller_id.strip()
    marketplace_id = marketplace_id.strip()
    msku = msku.strip()
    local_sku = local_sku.strip()

    if not all([seller_id, marketplace_id, msku, local_sku]):
        raise ValueError("配对缺少 seller_id / marketplace_id / msku / local_sku")

    try:
        client = _require_client()
        body = {
            "seller_id": seller_id,
            "marketplace_id": marketplace_id,
            "msku": msku,
            "sku": local_sku,
            "is_sync_pic": is_sync_pic,
        }
        response = client.request("POST", "/erp/sc/storage/product/link", body)
        if not is_ok_code(response.get("code")):
            raise RuntimeError(api_error(response, "SKU 配对失败"))
        return response
    except Exception as exc:
        if not is_whitelist_error(exc):
            raise
        proxied = remote_post(
            "/api/proxy/pair",
            {
                "seller_id": seller_id,
                "marketplace_id": marketplace_id,
                "msku": msku,
                "local_sku": local_sku,
                "is_sync_pic": is_sync_pic,
            },
        )
        if proxied and proxied.get("code") == 1:
            return proxied.get("data") or proxied
        raise RuntimeError(f"SKU 配对失败：{exc}") from exc
