from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from publish_service import build_publish_item


IMAGE_ATTR_KEYS = (
    "main_product_image_locator",
    "other_product_image_locator_1",
    "other_product_image_locator_2",
    "other_product_image_locator_3",
    "other_product_image_locator_4",
    "other_product_image_locator_5",
    "other_product_image_locator_6",
    "other_product_image_locator_7",
    "other_product_image_locator_8",
)


def _attr_values(attributes: dict[str, Any], key: str) -> list[str]:
    raw = attributes.get(key)
    if raw is None:
        return []
    if isinstance(raw, list):
        values: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                for field in ("value", "media_location", "url"):
                    if item.get(field):
                        values.append(str(item[field]).strip())
                        break
            elif item:
                values.append(str(item).strip())
        return [value for value in values if value]
    return [str(raw).strip()] if str(raw).strip() else []


def _collect_image_urls(attributes: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in IMAGE_ATTR_KEYS:
        urls.extend(_attr_values(attributes, key))
    return urls


def validate_publish_payload(payload: dict[str, Any]) -> None:
    store_id = int(payload.get("store_id") or 0)
    if store_id <= 0:
        raise ValueError("请选择店铺")

    msku = str(payload.get("msku") or payload.get("raw_form", {}).get("seller_sku") or "").strip()
    if not msku:
        raise ValueError("请填写 Parent SKU / MSKU")

    product_type = str(payload.get("product_type") or "").strip()
    if not product_type:
        raise ValueError("请选择产品分类（product_type）")

    raw_form = payload.get("raw_form") or {}
    item_name = str(raw_form.get("item_name") or "").strip()
    if not item_name:
        raise ValueError("请填写产品标题")

    brand = str(raw_form.get("brand") or "").strip()
    if not brand:
        raise ValueError("请填写品牌")

    build_publish_item(payload)

    attributes = payload.get("attributes") or {}
    image_urls = _collect_image_urls(attributes)
    if not image_urls:
        raise ValueError("请至少上传 1 张商品图片")

    for url in image_urls:
        if url.startswith("data:"):
            raise ValueError("图片不能使用 base64，请上传或填写公网图片 URL")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"图片 URL 无效：{url}")
        if parsed.scheme == "http" and os.environ.get("ALLOW_HTTP_IMAGES", "").strip() != "1":
            raise ValueError(
                "图片 URL 必须使用 HTTPS。请配置 OSS 或在 .env 设置 ALLOW_HTTP_IMAGES=1（不推荐生产环境）"
            )

    fulfillment = attributes.get("fulfillment_availability")
    channel = ""
    if isinstance(fulfillment, list) and fulfillment:
        first = fulfillment[0]
        if isinstance(first, dict):
            channel = str(first.get("fulfillment_channel_code") or "").strip()
    if channel == "DEFAULT":
        shipping = _attr_values(attributes, "merchant_shipping_group")
        if not shipping or shipping[0] in {"", "template_mock_1"}:
            raise ValueError("FBM 配送必须选择真实运费模板")
