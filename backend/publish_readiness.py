"""Publish readiness checks for listing score (aligned with publish_validator)."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from attribute_presets import resolve_preset
from listing_rubrics import extract_rubric_attributes


def _check(*, rule_id: str, passed: bool, message: str, fix: str = "") -> dict[str, Any]:
    return {
        "id": rule_id,
        "passed": passed,
        "message": message,
        "how_to_fix": fix,
    }


def check_publish_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    """Non-throwing publish readiness audit for scoring UI."""
    checks: list[dict[str, Any]] = []
    brand = str(payload.get("brand") or "").strip()
    manufacturer = str(payload.get("manufacturer") or brand).strip()
    product_type = str(payload.get("product_type") or payload.get("category") or "").strip()
    title = str(payload.get("title") or "").strip()
    msku = str(payload.get("msku") or payload.get("seller_sku") or payload.get("parent_sku") or "").strip()

    img = payload.get("image_count")
    images_linked = bool(payload.get("images_linked"))
    has_images = (isinstance(img, int) and img >= 1) or images_linked

    attrs = extract_rubric_attributes(payload)
    if isinstance(payload.get("attributes"), dict):
        attrs = {**attrs, **{k: str(v) for k, v in payload["attributes"].items() if v}}

    checks.append(_check(
        rule_id="pub_brand",
        passed=bool(brand),
        message="已填写品牌" if brand else "缺少品牌（刊登必填）",
        fix="在产品页或评分补充信息中填写 brand",
    ))
    checks.append(_check(
        rule_id="pub_manufacturer",
        passed=bool(manufacturer),
        message="已填写制造商" if manufacturer else "缺少制造商",
        fix="填写 manufacturer，通常与品牌一致",
    ))
    checks.append(_check(
        rule_id="pub_product_type",
        passed=bool(product_type),
        message=f"Product type: {product_type}" if product_type else "未选择 product_type",
        fix="选择产品分类（product_type）",
    ))
    checks.append(_check(
        rule_id="pub_title",
        passed=bool(title),
        message="标题已填写" if title else "缺少 item_name / 标题",
        fix="填写产品标题",
    ))
    checks.append(_check(
        rule_id="pub_images",
        passed=has_images,
        message=(
            f"已关联 {img} 张图片" if isinstance(img, int) and img >= 1
            else "已从产品页导入图片" if images_linked
            else "未确认商品图片（刊登至少 1 张公网 URL）"
        ),
        fix="从产品页导入或上传至少 1 张 HTTPS 图片",
    ))
    checks.append(_check(
        rule_id="pub_msku",
        passed=bool(msku),
        message=f"MSKU: {msku}" if msku else "未填写 Parent SKU / MSKU",
        fix="填写 seller_sku（刊登必填）",
    ))

    if product_type:
        preset = resolve_preset(product_type)
        required = preset.get("required_keys") or []
        flat = {**attrs, **{k: str(payload.get(k) or "") for k in payload if payload.get(k)}}
        skip_keys = {
            "list_price_currency", "list_price", "supplier_declared_dg_hz_regulation",
            "contains_liquid_contents", "required_product_compliance_certificate",
        }
        missing_attrs = [
            key for key in required
            if key not in skip_keys and not str(flat.get(key) or "").strip()
        ]
        if not missing_attrs:
            checks.append(_check(
                rule_id="pub_schema_attrs",
                passed=True,
                message=f"类目 {product_type} 核心属性已填写",
            ))
        else:
            preview = ", ".join(missing_attrs[:6])
            suffix = f" …(+{len(missing_attrs) - 6})" if len(missing_attrs) > 6 else ""
            checks.append(_check(
                rule_id="pub_schema_attrs",
                passed=False,
                message=f"缺少 schema 属性: {preview}{suffix}",
                fix="在产品表单补全类目必填属性后再刊登",
            ))

    image_urls = payload.get("product_images") or payload.get("image_urls") or []
    if isinstance(image_urls, str):
        try:
            image_urls = json.loads(image_urls)
        except Exception:
            image_urls = [image_urls] if image_urls else []
    if image_urls and isinstance(image_urls, list):
        bad = any(
            str(u.get("url") if isinstance(u, dict) else u).strip().startswith("data:")
            for u in image_urls
            if (u.get("url") if isinstance(u, dict) else u)
        )
        if bad:
            checks.append(_check(
                rule_id="pub_image_urls",
                passed=False,
                message="图片含 base64 或无效 URL",
                fix="使用 HTTPS 公网图片 URL",
            ))
        else:
            checks.append(_check(
                rule_id="pub_image_urls",
                passed=True,
                message="图片 URL 格式有效",
            ))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    score = int(round(passed / total * 100)) if total else 0
    issues = [
        {"issue": c["message"], "how_to_fix": c.get("how_to_fix", ""), "source": "publish"}
        for c in checks if not c["passed"]
    ]
    critical = {"pub_brand", "pub_product_type", "pub_title", "pub_images"}
    return {
        "score": score,
        "max": 100,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "issues": issues,
        "ready": score >= 80 and all(c["passed"] for c in checks if c["id"] in critical),
    }
