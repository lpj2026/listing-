from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from attribute_presets import apply_product_type_layout, expand_required_dimension_keys, summarize_required_fields
from attribute_schema import get_mock_attributes
from lingxing_client import LingxingClient
from lingxing_utils import api_error, is_ok_code
from remote_proxy import is_whitelist_error, remote_get


SKIP_SCHEMA_KEYS = {
    "item_name",
    "brand",
    "manufacturer",
    "bullet_point",
    "product_description",
    "generic_keyword",
    "main_product_image_locator",
    "purchasable_offer",
    "fulfillment_availability",
    "supplier_declared_has_product_identifier_exemption",
    "externally_assigned_product_identifier",
    "merchant_shipping_group",
    "item_type_keyword",
    "recommended_browse_nodes",
}

# Baseline required keys handled outside the attribute panel or auto-filled at publish time.
BASELINE_PANEL_SKIP = {
    "fulfillment_availability",
    "merchant_shipping_group",
    "externally_assigned_product_identifier",
    "merchant_suggested_asin",
    "manufacturer",
    "included_components",
}

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_CACHE_DIR = ROOT_DIR / "data" / "schema_cache"
SCHEMA_CACHE_SECONDS = int(os.environ.get("SCHEMA_CACHE_SECONDS", str(24 * 60 * 60)))

GROUP_ORDER = ["核心属性", "汽配属性", "包装物流", "合规安全", "价格与状态", "其他属性"]

FIELD_DEFAULTS = {
    "number_of_items": "1",
    "exterior_finish": "machined",
    "automotive_fit_type": "vehicle_specific_fit",
    "list_price_currency": "USD",
    "number_of_boxes": "1",
    "contains_liquid_contents": "false",
    "is_assembly_required": "false",
    "required_product_compliance_certificate": "Not Applicable",
    "country_of_origin": "CN",
    "supplier_declared_dg_hz_regulation": "not_applicable",
    "warranty_description": "2 years",
}

FIELD_ZH_LABELS = {
    "model_number": "型号",
    "model_name": "型号名称",
    "part_number": "零件编号",
    "included_components": "所包含组件",
    "automotive_fit_type": "汽车适配类型",
    "item_package_dimensions": "包装尺寸",
    "item_package_weight": "包装重量",
    "number_of_boxes": "箱数",
    "contains_liquid_contents": "是否含液体",
    "is_assembly_required": "需要组装",
    "required_product_compliance_certificate": "产品合规证书",
    "country_of_origin": "原产国",
    "supplier_declared_dg_hz_regulation": "危险商品规管",
    "warranty_description": "保修说明",
    "list_price": "不含税价目表",
    "list_price_currency": "价目表货币",
    "exterior_finish": "外饰面",
    "number_of_items": "产品数量",
    "auto_part_position": "安装位置",
    "condition_type": "物品状况",
    "variation_theme": "变种主题",
}

THEME_TOKEN_ZH = {
    "BATTERY_DESCRIPTION": "电池_描述",
    "CAPACITY": "容量",
    "COLOR": "颜色",
    "COLOR_NAME": "颜色名称",
    "CONFIGURATION": "配置",
    "CUP_SIZE": "罩杯尺寸",
    "CUSTOMER_PACKAGE_TYPE": "客户包装类型",
    "EDITION": "版本",
    "FIT_TYPE": "适配类型",
    "GRIP_SIZE": "握把尺寸",
    "HAND_ORIENTATION": "惯用手",
    "INSIDE_DIAMETER": "内径",
    "INSIDE_DIAMETER_STRING": "内径",
    "ITEM_DIAMETER": "商品直径",
    "ITEM_DIAMETER_STRING": "商品直径",
    "ITEM_DISPLAY_HEIGHT": "项目显示高度",
    "ITEM_DISPLAY_LENGTH": "项目显示长度",
    "ITEM_DISPLAY_WEIGHT": "项目显示重量",
    "ITEM_FORM": "商品形态",
    "ITEM_LENGTH": "商品长度",
    "ITEM_LENGTH_STRING": "商品长度",
    "ITEM_PACKAGE_QUANTITY": "包装数量",
    "ITEM_SHAPE": "商品形状",
    "LEG_LENGTH": "腿长",
    "LENGTH_RANGE": "长度范围",
    "LENS_COLOR": "镜片颜色",
    "MATERIAL": "材质",
    "MATERIAL_TYPE": "材质类型",
    "METAL_TYPE": "金属类型",
    "MODEL": "型号",
    "MODEL_NAME": "型号名称",
    "MODEL_NUMBER": "型号编号",
    "NOMINAL_WALL_THICKNESS": "公称壁厚",
    "NUMBER_OF_ITEMS": "商品数量",
    "ORIENTATION": "方向",
    "OUTSIDE_DIAMETER": "外径",
    "PART_NUMBER": "零件编号",
    "PATTERN": "图案",
    "PATTERN_NAME": "图案名称",
    "SCENT": "香味",
    "SET_NAME": "套装名称",
    "SHAFT": "杆身",
    "SIZE": "尺寸",
    "SIZE_NAME": "尺寸名称",
    "STYLE": "风格",
    "STYLE_NAME": "风格名称",
    "TEMPERATURE_RATING": "耐温等级",
    "WALL_THICKNESS_STRING": "壁厚",
}

TERM_ZH_LABELS = {
    "abpa": "ABPA",
    "accessory": "配件",
    "act": "法案",
    "acknowledgement": "确认",
    "address": "地址",
    "american": "美国",
    "assembly": "组装",
    "auto": "汽车",
    "automotive": "汽车",
    "battery": "电池",
    "batteries": "电池",
    "brand": "品牌",
    "box": "箱",
    "boxes": "箱数",
    "california": "加州",
    "certificate": "证书",
    "certification": "认证",
    "color": "颜色",
    "compliance": "合规",
    "component": "组件",
    "components": "组件",
    "condition": "状况",
    "contains": "包含",
    "content": "内容",
    "contents": "内容",
    "contract": "合同",
    "country": "国家",
    "currency": "货币",
    "dangerous": "危险",
    "description": "描述",
    "dimension": "尺寸",
    "dimensions": "尺寸",
    "exterior": "外部",
    "finish": "表面处理",
    "fit": "适配",
    "fulfillment": "配送",
    "government": "政府",
    "height": "高度",
    "information": "信息",
    "item": "商品",
    "items": "件数",
    "length": "长度",
    "liquid": "液体",
    "list": "标价",
    "manufacturer": "制造商",
    "model": "型号",
    "name": "名称",
    "number": "编号",
    "origin": "原产地",
    "package": "包装",
    "part": "零件",
    "parts": "零件",
    "partslink": "PartsLink",
    "position": "位置",
    "price": "价格",
    "product": "产品",
    "regulation": "规管",
    "regulations": "规管",
    "required": "必需",
    "specific": "特定",
    "supplier": "供应商",
    "type": "类型",
    "warranty": "保修",
    "weight": "重量",
    "width": "宽度",
}

VALUE_ZH_LABELS = {
    "vehicle_specific_fit": "特定车型",
    "universal_fit": "通用",
    "Not Applicable": "不适用",
    "California Air Review Board (CARB)": "加州空气资源委员会",
    "false": "否",
    "true": "是",
    "No": "否",
    "Yes": "是",
    "not_applicable": "不适用",
    "unknown": "未知",
    "other": "其他",
    "storage": "存储",
    "transportation": "运输",
    "waste": "废物",
    "ghs": "全球统一制度",
    "new_new": "新品",
    "new": "新品",
    "machined": "机加工",
    "brushed": "拉丝",
    "chrome": "镀铬",
    "milled": "铣削",
    "painted": "已涂漆",
    "polished": "抛光",
    "CN": "中国",
    "US": "美国",
    "DE": "德国",
    "USD": "美元",
    "CAD": "加元",
    "MXN": "墨西哥比索",
    "inches": "英寸",
    "centimeters": "厘米",
    "grams": "克",
    "kilograms": "公斤",
    "pounds": "磅",
    "ounces": "盎司",
    "milligrams": "毫克",
    "tons": "吨",
    "hundredths_pounds": "百分之一磅",
}


def _json_obj(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _cache_path(marketplace_id: str, product_type: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{marketplace_id}_{product_type}")
    return SCHEMA_CACHE_DIR / f"{safe}.json"


def _load_schema_cache(marketplace_id: str, product_type: str) -> dict[str, Any] | None:
    path = _cache_path(marketplace_id, product_type)
    if not path.exists() or time.time() - path.stat().st_mtime > SCHEMA_CACHE_SECONDS:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_schema_cache(marketplace_id: str, product_type: str, payload: dict[str, Any]) -> None:
    SCHEMA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(marketplace_id, product_type).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _find_schema(node: Any, depth: int = 0) -> dict[str, Any]:
    """Lingxing may wrap the Amazon product type schema as nested JSON strings."""
    if depth > 8:
        return {}
    node = _json_obj(node)
    properties = node.get("properties")
    if isinstance(properties, dict) and properties:
        return node
    for value in node.values():
        found = _find_schema(value, depth + 1)
        if found:
            return found
    return {}


def _find_properties(node: Any, depth: int = 0) -> dict[str, Any]:
    schema = _find_schema(node, depth)
    properties = schema.get("properties")
    return properties if isinstance(properties, dict) else {}


def _item_properties(prop: dict[str, Any]) -> dict[str, Any]:
    items = prop.get("items") or {}
    if not isinstance(items, dict):
        return {}
    properties = items.get("properties") or {}
    return properties if isinstance(properties, dict) else {}


def _value_schema(prop: dict[str, Any]) -> dict[str, Any]:
    item_props = _item_properties(prop)
    value = item_props.get("value")
    if isinstance(value, dict):
        return value
    media_location = item_props.get("media_location")
    if isinstance(media_location, dict):
        return media_location
    return prop


def _primary_value_key(prop: dict[str, Any]) -> str:
    item_props = _item_properties(prop)
    for key in ("value", "media_location"):
        if key in item_props:
            return key
    for key in item_props:
        if key not in {"marketplace_id", "language_tag", "unit"}:
            return str(key)
    return "value"


def _first_schema(*schemas: Any) -> dict[str, Any]:
    for schema in schemas:
        if isinstance(schema, dict):
            return schema
    return {}


def _schema_type(schema: dict[str, Any]) -> str:
    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        raw_type = next((item for item in raw_type if item != "null"), raw_type[0] if raw_type else "string")
    return str(raw_type or "string")


def _dimension_parts(prop: dict[str, Any]) -> list[str]:
    item_props = _item_properties(prop)
    parts = [part for part in ("length", "width", "height") if part in item_props]
    return parts or ["length", "width", "height"]


def _unit_count_type_options(prop: dict[str, Any]) -> list[dict[str, str]]:
    item_props = _item_properties(prop)
    type_schema = item_props.get("type")
    if not isinstance(type_schema, dict):
        return [{"value": "Count", "label": "Count(件)"}]
    value_schema = type_schema.get("properties", {}).get("value", {})
    if not isinstance(value_schema, dict):
        return [{"value": "Count", "label": "Count(件)"}]
    enum_values = list(value_schema.get("enum") or ["Count"])
    enum_names = list(value_schema.get("enumNames") or enum_values)
    return [
        {
            "value": str(value),
            "label": str(enum_names[index] if index < len(enum_names) else value),
        }
        for index, value in enumerate(enum_values)
    ]


def _field_type(key: str, prop: dict[str, Any]) -> str:
    if key in {"item_package_dimensions", "item_length_width"}:
        return "dimensions"
    if key == "unit_count":
        return "unit_count"
    item_props = _item_properties(prop)
    value_schema = _value_schema(prop)
    if {"value", "unit"}.issubset(item_props.keys()):
        return "unit"
    if value_schema.get("format") == "date":
        return "date"
    if value_schema.get("format") in {"uri", "url"} or key.endswith("_url"):
        return "url"
    if value_schema.get("enum"):
        max_items = int(prop.get("maxItems") or 1)
        return "checkbox_group" if max_items > 1 else "select"
    raw_type = _schema_type(value_schema)
    if raw_type == "boolean":
        return "select"
    if raw_type in {"integer", "number"}:
        return "number"
    return "text"


def _field_options(prop: dict[str, Any]) -> list[dict[str, str]]:
    value_schema = _value_schema(prop)
    enum_values = list(value_schema.get("enum") or [])
    enum_names = list(value_schema.get("enumNames") or value_schema.get("enum_names") or enum_values)
    if not enum_values:
        for key in ("oneOf", "anyOf"):
            for item in value_schema.get(key) or []:
                if not isinstance(item, dict):
                    continue
                enum_value = item.get("const")
                if enum_value is None:
                    nested = item.get("enum") or []
                    enum_value = nested[0] if nested else None
                if enum_value is not None:
                    enum_values.append(enum_value)
                    enum_names.append(item.get("title") or item.get("description") or enum_value)
    if _schema_type(value_schema) == "boolean" and not enum_values:
        enum_values = ["false", "true"]
        enum_names = ["No", "Yes"]
    options = []
    for index, value in enumerate(enum_values):
        label = enum_names[index] if index < len(enum_names) else value
        value_text = str(value)
        label_text = str(label)
        zh = VALUE_ZH_LABELS.get(value_text) or VALUE_ZH_LABELS.get(label_text)
        if zh and zh not in label_text:
            label_text = f"{label_text}({zh})"
        options.append({"value": value_text, "label": label_text})
    return options


def _int_constraint(schema: dict[str, Any], key: str) -> int | None:
    try:
        value = schema.get(key)
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _number_constraint(schema: dict[str, Any], key: str) -> int | float | None:
    value = schema.get(key)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _field_constraints(prop: dict[str, Any], value_schema: dict[str, Any]) -> dict[str, Any]:
    constraints: dict[str, Any] = {}
    for source, target in [
        ("minLength", "min_length"),
        ("maxLength", "max_length"),
        ("minItems", "min_items"),
        ("maxItems", "max_items"),
    ]:
        value = _int_constraint(value_schema, source)
        if value is None and source in {"minItems", "maxItems"}:
            value = _int_constraint(prop, source)
        if value is not None:
            constraints[target] = value
    for source, target in [
        ("minimum", "minimum"),
        ("maximum", "maximum"),
        ("exclusiveMinimum", "exclusive_minimum"),
        ("exclusiveMaximum", "exclusive_maximum"),
    ]:
        value = _number_constraint(value_schema, source)
        if value is not None:
            constraints[target] = value
    if value_schema.get("pattern"):
        constraints["pattern"] = str(value_schema["pattern"])
    if value_schema.get("format"):
        constraints["format"] = str(value_schema["format"])
    return constraints


def _unit_options(prop: dict[str, Any]) -> list[dict[str, str]]:
    unit_schema = _item_properties(prop).get("unit")
    if not isinstance(unit_schema, dict):
        return []
    enum_values = unit_schema.get("enum") or []
    enum_names = unit_schema.get("enumNames") or enum_values
    return [
        {
            "value": str(value),
            "label": (
                f"{enum_names[index] if index < len(enum_names) else value}"
                f"({VALUE_ZH_LABELS[str(value)]})"
                if str(value) in VALUE_ZH_LABELS
                else str(enum_names[index] if index < len(enum_names) else value)
            ),
        }
        for index, value in enumerate(enum_values)
    ]


def _schema_required_keys(schema: dict[str, Any]) -> set[str]:
    required = schema.get("required") or []
    return {str(item) for item in required if item}


def _extract_condition_from_property(key: str, schema: dict[str, Any]) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    node = schema
    for child_key in ("contains", "items"):
        if isinstance(node.get(child_key), dict):
            node = node[child_key]
    props = node.get("properties") if isinstance(node, dict) else {}
    if isinstance(props, dict) and isinstance(props.get("value"), dict):
        value_schema = props["value"]
    else:
        value_schema = node if isinstance(node, dict) else {}

    values = value_schema.get("enum")
    if values is None and value_schema.get("const") is not None:
        values = [value_schema["const"]]
    if values is None and isinstance(value_schema.get("not"), dict):
        not_schema = value_schema["not"]
        not_values = not_schema.get("enum")
        if not_values is None and not_schema.get("const") is not None:
            not_values = [not_schema["const"]]
        if not_values is not None:
            conditions.append({"field": key, "operator": "not_in", "values": [str(item) for item in not_values]})
    if values is not None:
        conditions.append({"field": key, "operator": "in", "values": [str(item) for item in values]})

    required = node.get("required") if isinstance(node, dict) else []
    if isinstance(required, list) and required and not conditions:
        conditions.append({"field": key, "operator": "present"})
    return conditions


def _extract_conditions(if_schema: Any) -> list[dict[str, Any]]:
    schema = _json_obj(if_schema)
    conditions: list[dict[str, Any]] = []
    props = schema.get("properties") or {}
    if isinstance(props, dict):
        for key, prop_schema in props.items():
            if isinstance(prop_schema, dict):
                conditions.extend(_extract_condition_from_property(str(key), prop_schema))
    for key in ("allOf", "anyOf"):
        for item in schema.get(key) or []:
            if isinstance(item, dict):
                nested = _extract_conditions(item)
                if nested:
                    conditions.extend(nested)
    return conditions


def _extract_required_targets(then_schema: Any) -> list[str]:
    schema = _json_obj(then_schema)
    targets = [str(item) for item in schema.get("required") or [] if item]
    props = schema.get("properties") or {}
    if isinstance(props, dict):
        for key, prop_schema in props.items():
            if isinstance(prop_schema, dict) and (prop_schema.get("minItems") or prop_schema.get("required")):
                targets.append(str(key))
    return sorted(set(targets))


def _extract_rules(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        current = _json_obj(node)
        if not current:
            return
        if current.get("if") and current.get("then"):
            when = _extract_conditions(current["if"])
            targets = _extract_required_targets(current["then"])
            if when and targets:
                rules.append({"when": when, "require": targets, "show": targets})
        for key in ("allOf", "anyOf", "oneOf"):
            for item in current.get(key) or []:
                visit(item)
        for item in (current.get("dependentSchemas") or {}).values():
            visit(item)

    visit(schema)
    return rules


def _exemption_requirement(if_schema: Any) -> str | None:
    """Return 'true', 'false', or None if the if-clause constrains UPC exemption."""

    def walk(node: Any) -> str | None:
        current = _json_obj(node)
        if not current:
            return None
        props = current.get("properties") or {}
        exemption = props.get("supplier_declared_has_product_identifier_exemption")
        if isinstance(exemption, dict):
            contains = exemption.get("contains") or {}
            value_schema = contains.get("properties", {}).get("value", {})
            enum_values = [str(item).lower() for item in value_schema.get("enum") or []]
            if enum_values == ["false"]:
                return "false"
            if enum_values == ["true"]:
                return "true"
        for key in ("anyOf", "allOf", "not"):
            items = current.get(key)
            if isinstance(items, list):
                results = [walk(item) for item in items]
                results = [item for item in results if item]
                if results:
                    return results[0]
            elif isinstance(items, dict):
                found = walk(items)
                if found:
                    return found
        return None

    return walk(if_schema)


def _matches_baseline_listing(if_schema: Any, *, has_fulfillment: bool = True, is_single_sku: bool = True, has_upc_exemption: bool = True) -> bool:
    """Match Amazon allOf rules for a default single-SKU listing with quantity and UPC exemption."""
    exemption_req = _exemption_requirement(if_schema)
    if exemption_req == "false":
        return not has_upc_exemption
    if exemption_req == "true":
        return has_upc_exemption

    node = _json_obj(if_schema)
    if not node:
        return False
    if "anyOf" in node:
        return any(
            _matches_baseline_listing(item, has_fulfillment=has_fulfillment, is_single_sku=is_single_sku, has_upc_exemption=has_upc_exemption)
            for item in node["anyOf"]
        )
    if "allOf" in node:
        return all(
            _matches_baseline_listing(item, has_fulfillment=has_fulfillment, is_single_sku=is_single_sku, has_upc_exemption=has_upc_exemption)
            for item in node["allOf"]
        )
    if "not" in node:
        inner = _json_obj(node["not"])
        required = inner.get("required") or []
        if "parentage_level" in required:
            return is_single_sku
        props = inner.get("properties") or {}
        parentage = props.get("parentage_level")
        if isinstance(parentage, dict):
            contains = parentage.get("contains") or {}
            value_schema = contains.get("properties", {}).get("value", {})
            if value_schema.get("enum") == ["parent"]:
                return is_single_sku
        return not _matches_baseline_listing(inner, has_fulfillment=has_fulfillment, is_single_sku=is_single_sku, has_upc_exemption=has_upc_exemption)

    required = [str(item) for item in node.get("required") or [] if item]
    props = node.get("properties") or {}
    if not isinstance(props, dict):
        props = {}

    if "fulfillment_availability" in required:
        return has_fulfillment
    if "fulfillment_availability" in props and has_fulfillment:
        return True

    exemption = props.get("supplier_declared_has_product_identifier_exemption")
    if isinstance(exemption, dict):
        for cond in _extract_conditions({"properties": {"supplier_declared_has_product_identifier_exemption": exemption}}):
            if cond.get("field") == "supplier_declared_has_product_identifier_exemption" and cond.get("operator") == "in":
                values = [str(item) for item in cond.get("values") or []]
                if "False" in values or "false" in values:
                    return has_upc_exemption
                if "True" in values or "true" in values:
                    return not has_upc_exemption

    if "parentage_level" in required or "child_parent_sku_relationship" in required:
        return not is_single_sku
    if "parentage_level" in props or "child_parent_sku_relationship" in props:
        return not is_single_sku

    return False


def compute_baseline_required(schema: dict[str, Any], rules: list[dict[str, Any]] | None = None) -> set[str]:
    """Fields Amazon requires for a typical single-SKU listing (quantity + UPC exemption)."""
    baseline = {key for key in _schema_required_keys(schema) if key not in SKIP_SCHEMA_KEYS}

    for item in schema.get("allOf") or []:
        if not isinstance(item, dict) or not item.get("if") or not item.get("then"):
            continue
        if not _matches_baseline_listing(item["if"]):
            continue
        baseline.update(_extract_required_targets(item["then"]))

    baseline -= BASELINE_PANEL_SKIP
    return expand_required_dimension_keys(baseline)


def _condition_matches_baseline(
    condition: dict[str, Any],
    *,
    has_fulfillment: bool,
    is_single_sku: bool,
    has_upc_exemption: bool,
) -> bool:
    field = str(condition.get("field") or "")
    operator = str(condition.get("operator") or "")
    values = [str(item) for item in condition.get("values") or []]

    if field == "fulfillment_availability":
        return has_fulfillment if operator == "present" else not has_fulfillment
    if field == "supplier_declared_has_product_identifier_exemption":
        if operator == "in":
            if "False" in values or "false" in values:
                return not has_upc_exemption
            if "True" in values or "true" in values:
                return has_upc_exemption
        if operator == "not_in":
            return True
    if field in {"parentage_level", "child_parent_sku_relationship", "variation_theme"}:
        if operator == "present":
            return not is_single_sku
        return is_single_sku
    if operator == "present":
        return False
    return False


def _field_group(key: str) -> str:
    lowered = key.lower()
    if key in {
        "model_number",
        "model_name",
        "part_number",
        "included_components",
        "automotive_fit_type",
    }:
        return "核心属性"
    if "package" in lowered or "box" in lowered or "weight" in lowered or "dimension" in lowered:
        return "包装物流"
    if any(token in lowered for token in ["compliance", "regulation", "liquid", "assembly", "country", "battery"]):
        return "合规安全"
    if any(token in lowered for token in ["auto", "automotive", "part", "fit", "position", "vehicle"]):
        return "汽配属性"
    if any(token in lowered for token in ["price", "condition"]):
        return "价格与状态"
    return "其他属性"


def _auto_zh_label(title: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title.lower())
    translated = [TERM_ZH_LABELS[word] for word in words if word in TERM_ZH_LABELS]
    if not translated:
        return ""
    result = "".join(translated)
    return result if result.lower() != title.lower() else ""


def _sort_key(field: dict[str, Any]) -> tuple[int, int, str]:
    group = str(field.get("group") or "其他属性")
    group_index = GROUP_ORDER.index(group) if group in GROUP_ORDER else len(GROUP_ORDER)
    common_index = 0 if not field.get("advanced") else 1
    return group_index, common_index, str(field.get("label_en") or field.get("key") or "")


def _label_prop(label_properties: dict[str, Any], key: str, prop: dict[str, Any]) -> dict[str, Any]:
    label_prop = label_properties.get(key)
    return label_prop if isinstance(label_prop, dict) else prop


def properties_to_fields(
    properties: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    label_properties: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root_schema = root_schema or {}
    label_properties = label_properties or {}
    rules = rules or []
    root_required = _schema_required_keys(root_schema)
    conditional_required = {
        key
        for rule in rules
        for key in rule.get("require", [])
    }
    fields: list[dict[str, Any]] = []
    for key, prop in properties.items():
        if key in SKIP_SCHEMA_KEYS or not isinstance(prop, dict):
            continue
        label_prop = _label_prop(label_properties, key, prop)
        value_schema = _value_schema(prop)
        item_props = _item_properties(prop)
        value_key = _primary_value_key(prop)
        required = key in root_required
        title = str(label_prop.get("title") or prop.get("title") or key)
        schema_required = required
        constraints = _field_constraints(prop, value_schema)
        field: dict[str, Any] = {
            "key": key,
            "label_en": str(prop.get("title") or title),
            "label_zh": FIELD_ZH_LABELS.get(key, "") or _auto_zh_label(title),
            "type": _field_type(key, prop),
            "required": required,
            "required_static": required,
            "schema_required": schema_required,
            "conditional_required": key in conditional_required,
            "schema": {
                "kind": "array",
                "value_type": _schema_type(value_schema),
                "value_key": value_key,
                "item_properties": sorted(item_props.keys()),
                "has_language_tag": "language_tag" in item_props,
                "has_marketplace_id": "marketplace_id" in item_props,
                "min_items": constraints.get("min_items"),
                "max_items": constraints.get("max_items"),
            },
            "constraints": constraints,
        }
        if prop.get("default") is not None:
            field["default"] = str(prop["default"])
        elif value_schema.get("default") is not None:
            field["default"] = str(value_schema["default"])
        elif key in FIELD_DEFAULTS:
            field["default"] = FIELD_DEFAULTS[key]
        group = _field_group(key)
        field["group"] = group
        field["advanced"] = not required and key not in conditional_required
        if key in conditional_required:
            field["conditional"] = True
        if label_prop.get("description") or prop.get("description"):
            field["help"] = str(label_prop.get("description") or prop["description"])
        if constraints.get("max_length"):
            field["maxlength"] = str(constraints["max_length"])
        if constraints.get("minimum") is not None:
            field["min"] = str(constraints["minimum"])
        if constraints.get("maximum") is not None:
            field["max"] = str(constraints["maximum"])
        options = _field_options(prop)
        if options:
            field["options"] = options
            if field["type"] in {"text", "number"}:
                field["type"] = "select"
            if field["type"] == "checkbox_group":
                field["layout"] = "grid"
                field["columns"] = 3
        if field["type"] == "unit":
            field["unit_key"] = f"{key}_unit"
            field["unit_options"] = _unit_options(prop)
            if field["unit_options"]:
                field["unit_default"] = field["unit_options"][0]["value"]
        if field["type"] == "dimensions":
            field["dimension_parts"] = _dimension_parts(prop)
            field["unit_key"] = f"{key}_unit"
            field["unit_options"] = [
                {"value": "inches", "label": "Inches(英寸)"},
                {"value": "centimeters", "label": "Centimeters(厘米)"},
            ]
            field["unit_default"] = "inches"
        if field["type"] == "unit_count":
            field["type_key"] = f"{key}_type"
            field["type_options"] = _unit_count_type_options(prop)
            field["type_default"] = "Count"
        fields.append(field)

    return sorted(fields, key=_sort_key)


def _variation_theme_label(value: str) -> str:
    token = value.strip()
    if not token:
        return value
    if token in THEME_TOKEN_ZH:
        return f"{token}({THEME_TOKEN_ZH[token]})"
    if "/" not in token:
        zh = _auto_zh_label(token.replace("_", " "))
        return f"{token}({zh})" if zh else token
    parts = []
    for part in token.split("/"):
        zh = THEME_TOKEN_ZH.get(part) or _auto_zh_label(part.replace("_", " "))
        parts.append(f"{part}({zh})" if zh else part)
    return "/".join(parts)


def extract_variation_themes(schema: dict[str, Any]) -> list[dict[str, str]]:
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    variation = props.get("variation_theme")
    if not isinstance(variation, dict):
        return []
    items = variation.get("items") if isinstance(variation.get("items"), dict) else {}
    name_schema = (items.get("properties") or {}).get("name")
    if not isinstance(name_schema, dict):
        return []
    enum_values = [str(item) for item in name_schema.get("enum") or [] if item]
    lifecycle = name_schema.get("$lifecycle") if isinstance(name_schema.get("$lifecycle"), dict) else {}
    deprecated = {str(item) for item in lifecycle.get("enumDeprecated") or [] if item}
    themes: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in enum_values:
        if value in deprecated or value in seen:
            continue
        seen.add(value)
        themes.append({"value": value, "label": _variation_theme_label(value)})
    return themes


def get_variation_themes(marketplace_id: str, product_type: str) -> dict[str, Any]:
    schema_result = get_schema(marketplace_id, product_type)
    themes = schema_result.get("variation_themes") or []
    return {
        "source": schema_result.get("source"),
        "product_type": product_type,
        "marketplace_id": marketplace_id,
        "themes": themes,
        "count": len(themes),
        "message": schema_result.get("message"),
    }


def _finalize_attribute_fields(
    fields: list[dict[str, Any]],
    product_type: str,
    *,
    baseline_required: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    flat = [field for field in fields if field.get("type") != "subsection"]
    layout = apply_product_type_layout(flat, product_type, baseline_required=baseline_required)
    return layout, summarize_required_fields(layout)


def get_schema(marketplace_id: str, product_type: str) -> dict[str, Any]:
    product_type = (product_type or "AUTO_PART").strip()
    marketplace_id = (marketplace_id or "ATVPDKIKX0DER").strip()
    client = LingxingClient.from_env()

    if client is None:
        attributes, required_summary = _finalize_attribute_fields(get_mock_attributes(product_type), product_type)
        return {
            "source": "mock",
            "product_type": product_type,
            "marketplace_id": marketplace_id,
            "properties": {},
            "properties_zh": {},
            "attributes": attributes,
            "rules": [],
            "variation_themes": [
                {"value": "COLOR", "label": "COLOR(颜色)"},
                {"value": "COLOR_NAME", "label": "COLOR_NAME(颜色名称)"},
                {"value": "SIZE", "label": "SIZE(尺寸)"},
                {"value": "SIZE_NAME", "label": "SIZE_NAME(尺寸名称)"},
            ],
            "required": required_summary["required_keys"],
            "required_summary": required_summary,
            "message": f"未配置领星凭证，当前展示 {product_type} 演示属性模板",
        }

    try:
        payload = _load_schema_cache(marketplace_id, product_type)
        cache_hit = payload is not None
        if payload is None:
            payload = client.request(
                "POST",
                "/basicOpen/openapi/publish/manage/getProductType",
                {"marketplaceId": marketplace_id, "productTypeOrigin": product_type},
            )
            if is_ok_code(payload.get("code")):
                _save_schema_cache(marketplace_id, product_type, payload)
        if not is_ok_code(payload.get("code")):
            raise RuntimeError(api_error(payload, "Schema 接口失败"))

        data = payload.get("data") or {}
        schema = _find_schema(data)
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        properties_zh = data.get("propertiesZh") or data.get("properties_zh") or properties
        rules = _extract_rules(schema)
        fields = properties_to_fields(
            properties if isinstance(properties, dict) else {},
            root_schema=schema,
            label_properties=properties_zh if isinstance(properties_zh, dict) else {},
            rules=rules,
        )
        if not fields:
            fields = [field for field in get_mock_attributes(product_type) if field.get("type") != "subsection"]
        baseline_required = compute_baseline_required(schema, rules)
        attributes, required_summary = _finalize_attribute_fields(fields, product_type, baseline_required=baseline_required)

        return {
            "source": "lingxing",
            "product_type": product_type,
            "marketplace_id": marketplace_id,
            "properties": properties,
            "properties_zh": properties_zh,
            "attributes": attributes,
            "rules": rules,
            "baseline_required_keys": sorted(baseline_required),
            "variation_themes": extract_variation_themes(schema),
            "required": required_summary["required_keys"],
            "required_summary": required_summary,
            "message": "数据来源：Schema 缓存" if cache_hit else "数据来源：领星 Schema API",
        }
    except Exception as exc:
        if is_whitelist_error(exc):
            proxied = remote_get(
                "/api/schema",
                {"marketplace_id": marketplace_id, "product_type": product_type},
            )
            if proxied and proxied.get("source") == "lingxing":
                flat = [field for field in proxied.get("attributes", []) if field.get("type") != "subsection"]
                baseline_required = set(proxied.get("baseline_required_keys") or [])
                attributes, required_summary = _finalize_attribute_fields(
                    flat,
                    product_type,
                    baseline_required=baseline_required,
                )
                proxied = dict(proxied)
                proxied["attributes"] = attributes
                proxied["required_summary"] = required_summary
                proxied["required"] = required_summary["required_keys"]
                return proxied

        hint = str(exc)
        if is_whitelist_error(exc):
            hint = "领星 API 403：本机 IP 未在白名单，且阿里云代理不可用。"
        attributes, required_summary = _finalize_attribute_fields(get_mock_attributes(product_type), product_type)
        return {
            "source": "mock",
            "product_type": product_type,
            "marketplace_id": marketplace_id,
            "properties": {},
            "properties_zh": {},
            "attributes": attributes,
            "rules": [],
            "required": required_summary["required_keys"],
            "required_summary": required_summary,
            "message": f"领星 Schema 暂不可用，已回退 {product_type} 演示模板。{hint}",
        }
