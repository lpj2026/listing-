from __future__ import annotations

import ast
import json
import os
import re
from typing import Any

from lingxing_client import LingxingClient
from remote_proxy import is_whitelist_error, remote_get


DEFAULT_STORE_ID = int(os.environ.get("LINGXING_DEFAULT_STORE_ID", "12518"))

CATEGORY_ZH_LABELS = {
    "Amazon Explore": "亚马逊探索",
    "Amazon Instant Video": "亚马逊即时视频",
    "Appliances": "家用电器",
    "Apps & Games": "应用和游戏",
    "Arts, Crafts & Sewing": "艺术、手工和缝纫",
    "Automotive": "汽车用品",
    "Baby Products": "母婴用品",
    "Beauty & Personal Care": "美妆和个人护理",
    "Books": "图书",
    "Cell Phones & Accessories": "手机和配件",
    "Clothing, Shoes & Jewelry": "服装、鞋靴和珠宝",
    "Electronics": "电子产品",
    "Health & Household": "健康和家居",
    "Home & Kitchen": "家居和厨房",
    "Industrial & Scientific": "工业和科学",
    "Kitchen & Dining": "厨房和餐饮",
    "Musical Instruments": "乐器",
    "Office Products": "办公用品",
    "Patio, Lawn & Garden": "庭院、草坪和花园",
    "Pet Supplies": "宠物用品",
    "Sports & Outdoors": "运动和户外",
    "Tools & Home Improvement": "工具和家装",
    "Toys & Games": "玩具和游戏",
    "Video Games": "视频游戏",
    "Car Care": "汽车养护",
    "Replacement Parts": "替换零件",
    "Car Electronics": "车载电子",
    "Automotive Pest Repellents": "汽车驱虫用品",
    "Cleaning Kits": "清洁套装",
    "Car Wash Equipment": "洗车设备",
    "Repellent Mats": "驱虫垫",
    "Repellent Sprays": "驱虫喷雾",
    "Ultrasonic Repellents": "超声波驱虫器",
    "Ignition Coils": "点火线圈",
    "Air Filters": "空气滤清器",
    "Dash Cameras": "行车记录仪",
    "Baby Gear": "婴儿用品",
    "Headphones": "耳机",
}

CATEGORY_TERM_ZH = {
    "accessories": "配件",
    "accessory": "配件",
    "adhesives": "粘合剂",
    "air": "空气",
    "amazon": "亚马逊",
    "and": "和",
    "appliances": "电器",
    "apps": "应用",
    "arranging": "布置",
    "art": "艺术",
    "arts": "艺术",
    "automotive": "汽车",
    "baby": "婴儿",
    "basket": "篮子",
    "baskets": "篮子",
    "beading": "串珠",
    "beauty": "美妆",
    "bells": "铃铛",
    "boas": "羽毛围巾",
    "books": "图书",
    "brads": "订书钉",
    "building": "搭建",
    "camera": "摄像头",
    "cameras": "摄像头",
    "candle": "蜡烛",
    "car": "汽车",
    "care": "养护",
    "cell": "手机",
    "ceramics": "陶瓷",
    "cleaners": "清洁用品",
    "clothing": "服装",
    "craft": "手工",
    "crafting": "手工制作",
    "crafts": "手工艺",
    "crochet": "钩针编织",
    "cut": "切割",
    "cutting": "切割",
    "decorating": "装饰",
    "decorations": "装饰",
    "dining": "餐饮",
    "doll": "玩偶",
    "drawing": "绘画",
    "electronics": "电子",
    "engraving": "雕刻",
    "equipment": "设备",
    "explore": "探索",
    "fabric": "布料",
    "face": "面部",
    "feathers": "羽毛",
    "fibers": "纤维",
    "filters": "滤清器",
    "foam": "泡沫",
    "foil": "箔片",
    "framing": "装裱",
    "games": "游戏",
    "gear": "用品",
    "gift": "礼品",
    "glitter": "闪粉",
    "gold": "金箔",
    "headphones": "耳机",
    "health": "健康",
    "hobby": "爱好",
    "home": "家居",
    "household": "家居",
    "improvement": "装修",
    "industrial": "工业",
    "instant": "即时",
    "instruments": "乐器",
    "jewelry": "珠宝",
    "kitchen": "厨房",
    "kits": "套装",
    "knitting": "编织",
    "knotting": "打结",
    "lace": "蕾丝",
    "lawn": "草坪",
    "leathercraft": "皮艺",
    "leaf": "箔片",
    "macrame": "绳编",
    "making": "制作",
    "metal": "金属",
    "mats": "垫",
    "model": "模型",
    "mosaic": "马赛克",
    "musical": "音乐",
    "needlework": "针线活",
    "office": "办公",
    "organization": "收纳",
    "outdoors": "户外",
    "painting": "绘画",
    "paper": "纸艺",
    "parts": "零件",
    "party": "派对",
    "patio": "庭院",
    "personal": "个人",
    "pet": "宠物",
    "phones": "手机",
    "picture": "画框",
    "pipe": "烟斗",
    "plastic": "塑料",
    "pom": "绒球",
    "poms": "绒球",
    "pottery": "陶艺",
    "printmaking": "版画",
    "products": "产品",
    "repellent": "驱虫",
    "repellents": "驱虫器",
    "replacement": "替换",
    "scientific": "科学",
    "scrapbooking": "剪贴簿",
    "sculpture": "雕塑",
    "sewing": "缝纫",
    "shoes": "鞋靴",
    "soap": "肥皂",
    "sports": "运动",
    "sprays": "喷雾",
    "stained": "彩色",
    "stamping": "印章",
    "sticks": "木棍",
    "storage": "存储",
    "suncatcher": "阳光捕手",
    "supplies": "用品",
    "tools": "工具",
    "toys": "玩具",
    "transport": "运输",
    "ultrasonic": "超声波",
    "video": "视频",
    "wash": "清洗",
    "wrapping": "包装",
    "garden": "花园",
    "glass": "玻璃",
    "floral": "花卉",
    "scratchboards": "刮画板",
}


def _translate_segment(segment: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", segment.lower())
    translated = [CATEGORY_TERM_ZH[word] for word in words if word in CATEGORY_TERM_ZH]
    return "".join(translated)


def category_zh_label(name: str) -> str:
    clean = str(name or "").strip()
    if not clean:
        return ""
    if clean in CATEGORY_ZH_LABELS:
        return CATEGORY_ZH_LABELS[clean]

    segments = re.split(r"\s*(?:,|&| and )\s*", clean, flags=re.IGNORECASE)
    parts = [_translate_segment(seg) for seg in segments if seg.strip()]
    parts = [part for part in parts if part]
    if not parts:
        return _translate_segment(clean)
    if len(parts) == 1:
        return parts[0]
    return "、".join(parts[:-1]) + "和" + parts[-1]


def category_display_name(name: str) -> str:
    clean = str(name or "").strip()
    zh = category_zh_label(clean)
    if not clean or not zh or zh in clean:
        return clean
    return f"{clean}({zh})"

# 本地无领星凭证时的演示数据，结构对标店小秘四级分类
MOCK_TREE: dict[str, list[dict[str, Any]]] = {
    "root": [
        {"id": "mock-auto", "name": "Automotive", "has_children": True},
        {"id": "mock-baby", "name": "Baby Products", "has_children": True},
        {"id": "mock-electronics", "name": "Electronics", "has_children": True},
        {"id": "mock-home", "name": "Home & Kitchen", "has_children": True},
    ],
    "mock-auto": [
        {"id": "mock-auto-care", "name": "Car Care", "has_children": True},
        {"id": "mock-auto-parts", "name": "Replacement Parts", "has_children": True, "product_type": "AUTO_PART"},
        {"id": "mock-auto-electronics", "name": "Car Electronics", "has_children": True},
    ],
    "mock-auto-care": [
        {
            "id": "mock-auto-pest",
            "name": "Automotive Pest Repellents",
            "has_children": True,
            "product_type": "PEST_CONTROL_DEVICE",
        },
        {"id": "mock-auto-clean", "name": "Cleaning Kits", "has_children": False, "product_type": "AUTO_ACCESSORY"},
        {"id": "mock-auto-wash", "name": "Car Wash Equipment", "has_children": False, "product_type": "AUTO_ACCESSORY"},
    ],
    "mock-auto-pest": [
        {
            "id": "mock-pest-mats",
            "name": "Repellent Mats",
            "has_children": False,
            "product_type": "AUTO_ACCESSORY",
            "browse_node_attributes": {"item_type_keyword": "automotive-repellent-mats"},
        },
        {
            "id": "mock-pest-spray",
            "name": "Repellent Sprays",
            "has_children": False,
            "product_type": "PEST_CONTROL_DEVICE",
            "browse_node_attributes": {"item_type_keyword": "automotive-repellent-sprays"},
        },
        {
            "id": "mock-pest-ultrasonic",
            "name": "Ultrasonic Repellents",
            "has_children": False,
            "product_type": "PEST_CONTROL_DEVICE",
            "browse_node_attributes": {"item_type_keyword": "ultrasonic-pest-repellents"},
        },
    ],
    "mock-auto-parts": [
        {
            "id": "mock-part-ignition",
            "name": "Ignition Coils",
            "has_children": False,
            "product_type": "IGNITION_COIL",
            "browse_node_attributes": {"item_type_keyword": "automotive-ignition-coils"},
        },
        {
            "id": "mock-part-filter",
            "name": "Air Filters",
            "has_children": False,
            "product_type": "AUTO_PART",
            "browse_node_attributes": {"item_type_keyword": "automotive-air-filters"},
        },
    ],
    "mock-auto-electronics": [
        {
            "id": "mock-dash-cam",
            "name": "Dash Cameras",
            "has_children": False,
            "product_type": "VEHICLE_CAMERA",
            "browse_node_attributes": {"item_type_keyword": "dash-cameras"},
        },
    ],
    "mock-baby": [
        {"id": "mock-baby-gear", "name": "Baby Gear", "has_children": False, "product_type": "BABY_PRODUCT"},
    ],
    "mock-electronics": [
        {"id": "mock-headphones", "name": "Headphones", "has_children": False, "product_type": "HEADPHONES"},
    ],
    "mock-home": [
        {"id": "mock-kitchen", "name": "Kitchen & Dining", "has_children": False, "product_type": "KITCHEN"},
    ],
}


def parse_browse_node_attributes(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw in (None, "", "[]", []):
        return {}
    if isinstance(raw, str):
        text = raw.strip()
        for candidate in (text, text.strip('"')):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, str):
                nested = parse_browse_node_attributes(parsed)
                if nested:
                    return nested
            try:
                literal = ast.literal_eval(candidate)
            except (SyntaxError, ValueError):
                literal = None
            if isinstance(literal, dict):
                return literal
    return {}


def normalize_product_type(raw: Any) -> str:
    if isinstance(raw, list):
        for item in raw:
            if item:
                return str(item)
        return ""
    return str(raw) if raw else ""


def normalize_category(item: dict[str, Any]) -> dict[str, Any]:
    node_id = (
        item.get("categoryUniqueId")
        or item.get("category_unique_id")
        or item.get("id")
        or item.get("browseNodeId")
        or ""
    )
    name = item.get("categoryName") or item.get("category_name") or item.get("name") or ""
    has_children = item.get("hasChildren")
    if has_children is None:
        has_children = item.get("has_children", 0)
    has_children = bool(int(has_children)) if str(has_children).isdigit() else bool(has_children)

    product_type = normalize_product_type(
        item.get("productTypeOrigin") or item.get("product_type") or item.get("productType") or ""
    )
    browse_attrs = parse_browse_node_attributes(
        item.get("browseNodeAttributes") or item.get("browse_node_attributes")
    )

    name_text = str(name)
    return {
        "id": str(node_id),
        "name": name_text,
        "name_zh": category_zh_label(name_text),
        "display_name": category_display_name(name_text),
        "has_children": has_children,
        "product_type": product_type,
        "browse_node_attributes": browse_attrs,
        "category_path_name": str(item.get("categoryPathName") or ""),
    }


def extract_category_items(payload: dict[str, Any], parent_id: str | None) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    if parent_id:
        items = data.get("categoryChildren") if isinstance(data, dict) else []
    elif isinstance(data, dict):
        items = data.get("category") or []
    else:
        items = data if isinstance(data, list) else []

    if not isinstance(items, list):
        raise RuntimeError(f"领星分类返回格式异常: {payload}")
    return items


def _mock_list(parent_id: str | None) -> list[dict[str, Any]]:
    key = parent_id or "root"
    items = []
    for item in MOCK_TREE.get(key, []):
        node = dict(item)
        node["name_zh"] = category_zh_label(str(node.get("name") or ""))
        node["display_name"] = category_display_name(str(node.get("name") or ""))
        items.append(node)
    return items


def _lingxing_list(store_id: int, parent_id: str | None, client: LingxingClient) -> list[dict[str, Any]]:
    if parent_id:
        body = {"storeId": store_id, "categoryUniqueId": parent_id}
        path = "/basicOpen/openapi/publish/manage/categoryChildren"
    else:
        body = {"storeId": store_id}
        path = "/basicOpen/openapi/publish/manage/categoryRoot"

    payload = client.request("POST", path, body)
    code = str(payload.get("code"))
    if code not in {"0", "1", "200"}:
        raise RuntimeError(payload.get("msg") or payload.get("message") or f"领星分类接口失败: {payload}")

    items = extract_category_items(payload, parent_id)
    return [normalize_category(item) for item in items]


def list_categories(store_id: int | None = None, parent_id: str | None = None) -> dict[str, Any]:
    store_id = store_id or DEFAULT_STORE_ID
    # 本地店铺下拉使用的是序号 id，领星 API 需要真实 sid（如 12518）
    api_store_id = store_id if store_id >= 10000 else DEFAULT_STORE_ID
    client = LingxingClient.from_env()

    if client is None:
        return {
            "source": "mock",
            "store_id": store_id,
            "api_store_id": api_store_id,
            "parent_id": parent_id,
            "data": _mock_list(parent_id),
            "message": "未配置 LINGXING_APP_ID / LINGXING_APP_SECRET，当前展示演示分类数据",
        }

    try:
        data = _lingxing_list(api_store_id, parent_id, client)
        return {
            "source": "lingxing",
            "store_id": store_id,
            "api_store_id": api_store_id,
            "parent_id": parent_id,
            "data": data,
            "message": "数据来源：领星 API",
        }
    except Exception as exc:
        if is_whitelist_error(exc):
            proxy_path = "/api/categories/children" if parent_id else "/api/categories/root"
            proxy_params: dict[str, Any] = {"store_id": store_id}
            if parent_id:
                proxy_params["parent_id"] = parent_id
            proxied = remote_get(proxy_path, proxy_params)
            if proxied and proxied.get("source") == "lingxing":
                return proxied

        hint = str(exc)
        if is_whitelist_error(exc):
            hint = "领星 API 403：本机 IP 未在白名单，且阿里云代理不可用。"
        return {
            "source": "mock",
            "store_id": store_id,
            "api_store_id": api_store_id,
            "parent_id": parent_id,
            "data": _mock_list(parent_id),
            "message": f"领星接口暂不可用，已回退演示数据。{hint}",
        }


def search_mock_categories(keyword: str) -> list[dict[str, Any]]:
    keyword = keyword.strip().lower()
    if not keyword:
        return []

    results: list[dict[str, Any]] = []

    def walk(parent_key: str, path: list[str]) -> None:
        for node in MOCK_TREE.get(parent_key, []):
            display_name = category_display_name(str(node["name"]))
            current_path = path + [display_name]
            haystack = " > ".join(current_path).lower()
            if keyword in haystack or keyword in node["name"].lower() or keyword in display_name.lower():
                results.append(
                    {
                        "id": node["id"],
                        "name": node["name"],
                        "name_zh": category_zh_label(str(node["name"])),
                        "display_name": display_name,
                        "path": current_path,
                        "path_text": " > ".join(current_path),
                        "has_children": node.get("has_children", False),
                        "product_type": node.get("product_type", ""),
                        "browse_node_attributes": node.get("browse_node_attributes", {}),
                    }
                )
            if node.get("has_children"):
                walk(node["id"], current_path)

    walk("root", [])
    return results[:30]
