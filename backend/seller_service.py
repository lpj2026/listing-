from __future__ import annotations

from typing import Any

from lingxing_client import LingxingClient
from lingxing_utils import api_error, extract_list, is_ok_code
from remote_proxy import is_whitelist_error, remote_get
from stores_data import SITE_META, build_stores


COUNTRY_TO_SITE = {
    "美国": "US",
    "US": "US",
    "USA": "US",
    "加拿大": "CA",
    "CA": "CA",
    "墨西哥": "MX",
    "MX": "MX",
}


def _site_from_seller(item: dict[str, Any]) -> str:
    country = str(item.get("country") or item.get("site") or "").strip()
    if country in COUNTRY_TO_SITE:
        return COUNTRY_TO_SITE[country]
    name = str(item.get("name") or item.get("seller_name") or "")
    for code in ("US", "CA", "MX"):
        if name.endswith(f"-{code}") or name.endswith(f"--{code}"):
            return code
    return "US"


def normalize_seller(item: dict[str, Any]) -> dict[str, Any]:
    sid = int(item.get("sid") or item.get("store_id") or item.get("id") or 0)
    full_name = str(item.get("name") or item.get("seller_name") or item.get("account_name") or "")
    site_code = _site_from_seller(item)
    site_meta = SITE_META.get(site_code, SITE_META["US"])
    account = full_name
    for suffix in (f"-{site_code}", f"--{site_code}"):
        if full_name.endswith(suffix):
            account = full_name[: -len(suffix)]
            break

    return {
        "id": sid,
        "sid": sid,
        "account": account,
        "full_name": full_name,
        "site_code": site_code,
        "site_name": site_meta["site_name"],
        "marketplace_id": str(item.get("marketplace_id") or site_meta["marketplace_id"]),
        "seller_id": str(item.get("seller_id") or item.get("sellerId") or ""),
        "country": str(item.get("country") or site_meta["site_name"]),
    }


def _fetch_lingxing_stores(client: LingxingClient) -> list[dict[str, Any]]:
    payload = client.request("GET", "/erp/sc/data/seller/lists")
    if not is_ok_code(payload.get("code")):
        raise RuntimeError(api_error(payload, "店铺列表接口失败"))
    items = extract_list(payload)
    stores = [normalize_seller(item) for item in items if isinstance(item, dict)]
    return [store for store in stores if store["id"] > 0]


def list_stores() -> dict[str, Any]:
    client = LingxingClient.from_env()
    fallback = build_stores()

    if client is None:
        return {
            "source": "mock",
            "data": fallback,
            "message": "未配置领星凭证，当前展示本地店铺配置",
        }

    try:
        stores = _fetch_lingxing_stores(client)
        if not stores:
            raise RuntimeError("店铺列表为空")
        return {
            "source": "lingxing",
            "data": stores,
            "message": f"数据来源：领星 API（{len(stores)} 个店铺）",
        }
    except Exception as exc:
        if is_whitelist_error(exc):
            proxied = remote_get("/api/stores")
            if proxied and proxied.get("source") == "lingxing":
                return proxied

        hint = str(exc)
        if is_whitelist_error(exc):
            hint = "领星 API 403：本机 IP 未在白名单，且阿里云代理不可用。"
        return {
            "source": "mock",
            "data": fallback,
            "message": f"领星店铺接口暂不可用，已回退本地配置。{hint}",
        }
