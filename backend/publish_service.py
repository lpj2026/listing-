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


def build_publish_item(payload: dict[str, Any]) -> dict[str, Any]:
    msku = str(payload.get("msku") or payload.get("raw_form", {}).get("seller_sku") or "").strip()
    if not msku:
        raise ValueError("缺少 MSKU（seller_sku）")

    product_type = str(payload.get("product_type") or "AUTO_PART").strip()
    attributes = payload.get("attributes") or {}
    if not isinstance(attributes, dict) or not attributes:
        raise ValueError("缺少 attributes 商品资料")

    return {
        "sku": msku,
        "productType": product_type,
        "operationType": int(payload.get("operation_type", 0)),
        "attributes": attributes,
    }


def submit_publish(payload: dict[str, Any]) -> dict[str, Any]:
    store_id = int(payload.get("store_id") or 0)
    if store_id <= 0:
        raise ValueError("缺少 store_id")

    try:
        client = _require_client()
        body = {
            "store_id": store_id,
            "data": [build_publish_item(payload)],
        }
        response = client.request("POST", "/listing/publish/openapi/amazon/product/publish", body)
        if not is_ok_code(response.get("code")):
            raise RuntimeError(api_error(response, "刊登提交失败"))

        data = response.get("data") or {}
        record_unique_id = data.get("record_unique_id") or data.get("recordUniqueId") or ""
        if not record_unique_id:
            raise RuntimeError(f"刊登提交未返回 record_unique_id: {response}")

        return {
            "record_unique_id": str(record_unique_id),
            "request": body,
            "response": response,
        }
    except Exception as exc:
        if not is_whitelist_error(exc):
            raise
        proxied = remote_post("/api/proxy/publish", payload)
        if proxied and proxied.get("code") == 1 and proxied.get("data"):
            return proxied["data"]
        raise RuntimeError(f"领星刊登提交失败：{exc}") from exc


def query_publish_result(
    *,
    record_unique_id: str | None = None,
    store_id: int | None = None,
    sku: str | None = None,
    offset: int = 0,
    length: int = 20,
) -> dict[str, Any]:
    try:
        client = _require_client()
        body: dict[str, Any] = {"offset": offset, "length": length}
        if record_unique_id:
            body["record_unique_id"] = record_unique_id
        if store_id:
            body["store_id"] = store_id
        if sku:
            body["sku"] = sku

        response = client.request("POST", "/listing/publish/openapi/amazon/product/list", body)
        if not is_ok_code(response.get("code")):
            raise RuntimeError(api_error(response, "刊登结果查询失败"))

        items = extract_list(response)
        latest = items[0] if items else {}
        status = latest.get("status")
        status_map = {0: "PROCESSING", 1: "SUCCESS", 2: "FAILED"}
        return {
            "items": items,
            "latest": latest,
            "status": status,
            "status_text": status_map.get(status, "UNKNOWN"),
            "failure_reason": latest.get("failure_reason") or latest.get("failureReason") or "",
            "response": response,
        }
    except Exception as exc:
        if not is_whitelist_error(exc):
            raise
        proxied = remote_post(
            "/api/proxy/publish/query",
            {
                "record_unique_id": record_unique_id,
                "store_id": store_id,
                "sku": sku,
                "offset": offset,
                "length": length,
            },
        )
        if proxied and proxied.get("code") == 1 and proxied.get("data"):
            return proxied["data"]
        raise RuntimeError(f"领星刊登结果查询失败：{exc}") from exc
