from __future__ import annotations

from typing import Any

from lingxing_client import LingxingClient
from lingxing_utils import api_error, extract_list, is_ok_code
from remote_proxy import is_whitelist_error, remote_get


def _require_client() -> LingxingClient:
    client = LingxingClient.from_env()
    if client is None:
        raise RuntimeError("未配置 LINGXING_APP_ID / LINGXING_APP_SECRET")
    return client


def _normalize_template(item: dict[str, Any]) -> dict[str, str]:
    name = str(item.get("name") or item.get("templateName") or item.get("label") or "").strip()
    value = str(item.get("value") or item.get("id") or item.get("templateId") or "").strip()
    if not value:
        value = name
    return {"name": name or value, "value": value}


def list_merchant_shipping_groups(
    *,
    seller_id: str,
    marketplace_id: str,
    product_type: str,
    flag: int = 0,
) -> dict[str, Any]:
    seller_id = seller_id.strip()
    marketplace_id = marketplace_id.strip()
    product_type = product_type.strip() or "AUTO_PART"
    if not seller_id or not marketplace_id:
        raise ValueError("缺少 seller_id 或 marketplace_id")

    try:
        client = _require_client()
        response = client.request(
            "POST",
            "/basicOpen/openapi/publish/manage/getMerchantShippingGroup",
            {
                "seller_id": seller_id,
                "marketplace_id": marketplace_id,
                "product_type": product_type,
                "flag": flag,
            },
        )
        if not is_ok_code(response.get("code")):
            raise RuntimeError(api_error(response, "运费模板查询失败"))

        data = response.get("data")
        items: list[dict[str, Any]] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = extract_list(data) or data.get("merchantShippingGroup") or []
        templates = [_normalize_template(item) for item in items if isinstance(item, dict)]
        templates = [item for item in templates if item["value"]]
        return {
            "source": "lingxing",
            "data": templates,
            "message": "数据来源：领星 API",
        }
    except Exception as exc:
        if not is_whitelist_error(exc):
            raise
        proxied = remote_get(
            "/api/shipping-templates",
            {
                "seller_id": seller_id,
                "marketplace_id": marketplace_id,
                "product_type": product_type,
                "flag": flag,
            },
        )
        if proxied and proxied.get("data"):
            return proxied
        raise RuntimeError(f"运费模板查询失败：{exc}") from exc
