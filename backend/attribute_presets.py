from __future__ import annotations

from copy import deepcopy
from typing import Any

# 汽配及相关 product type 共用店小秘汽配属性布局
AUTOMOTIVE_TYPES = {
    "AUTO_PART",
    "IGNITION_COIL",
    "AUTO_ACCESSORY",
    "PEST_CONTROL_DEVICE",
    "VEHICLE_CAMERA",
}

AUTOMOTIVE_VISIBLE_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "exterior_finish",
    "part_number",
    "is_assembly_required",
    "included_components",
    "automotive_fit_type",
    "list_price_currency",
    "list_price",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_dimensions",
    "item_package_weight",
    "number_of_boxes",
    "country_of_origin",
    "warranty_description",
    "supplier_declared_dg_hz_regulation",
    "contains_liquid_contents",
    "required_product_compliance_certificate",
]

AUTOMOTIVE_REQUIRED_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "exterior_finish",
    "part_number",
    "is_assembly_required",
    "included_components",
    "automotive_fit_type",
    "list_price_currency",
    "list_price",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_dimensions",
    "item_package_weight",
    "number_of_boxes",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
    "contains_liquid_contents",
    "required_product_compliance_certificate",
]

AUTOMOTIVE_SECTIONS: list[dict[str, Any]] = [
    {
        "keys": [
            "model_number",
            "model_name",
            "number_of_items",
            "exterior_finish",
            "part_number",
            "is_assembly_required",
            "included_components",
            "automotive_fit_type",
        ],
    },
    {"title": "List Price(不含税价目表)", "keys": ["list_price_currency", "list_price"]},
    {
        "title": "Item Package Dimensions(包装尺寸)",
        "panel": True,
        "keys": [
            "item_package_length",
            "item_package_width",
            "item_package_height",
            "item_package_dimensions",
        ],
    },
    {
        "title": "Package Weight(包裹重量)",
        "panel": True,
        "keys": ["item_package_weight", "number_of_boxes"],
    },
    {
        "keys": [
            "country_of_origin",
            "warranty_description",
            "supplier_declared_dg_hz_regulation",
            "contains_liquid_contents",
            "required_product_compliance_certificate",
        ],
    },
]

HEADPHONES_VISIBLE_KEYS = [
    "headphones_form_factor",
    "headphones_ear_placement",
    "connectivity_technology",
    "noise_control",
    "color",
    "model_number",
    "model_name",
    "number_of_items",
    "list_price_currency",
    "list_price",
    "item_package_dimensions",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_weight",
    "number_of_boxes",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
    "contains_liquid_contents",
    "batteries_required",
    "batteries_included",
]

HEADPHONES_REQUIRED_KEYS = [
    "headphones_form_factor",
    "connectivity_technology",
    "model_number",
    "model_name",
    "number_of_items",
    "list_price_currency",
    "list_price",
    "item_package_dimensions",
    "item_package_weight",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
]

HEADPHONES_SECTIONS: list[dict[str, Any]] = [
    {
        "keys": [
            "headphones_form_factor",
            "headphones_ear_placement",
            "connectivity_technology",
            "noise_control",
            "color",
            "model_number",
            "model_name",
            "number_of_items",
        ],
    },
    {"title": "List Price(不含税价目表)", "keys": ["list_price_currency", "list_price"]},
    {
        "title": "Item Package Dimensions(包装尺寸)",
        "panel": True,
        "keys": [
            "item_package_length",
            "item_package_width",
            "item_package_height",
            "item_package_dimensions",
        ],
    },
    {"title": "Package Weight(包裹重量)", "panel": True, "keys": ["item_package_weight"]},
    {
        "keys": [
            "number_of_boxes",
            "country_of_origin",
            "supplier_declared_dg_hz_regulation",
            "contains_liquid_contents",
            "batteries_required",
            "batteries_included",
        ],
    },
]

BABY_VISIBLE_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "color",
    "material",
    "target_gender",
    "minimum_weight_recommendation",
    "maximum_weight_recommendation",
    "list_price_currency",
    "list_price",
    "item_package_dimensions",
    "item_package_weight",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
    "contains_liquid_contents",
    "is_assembly_required",
]

BABY_REQUIRED_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "list_price_currency",
    "list_price",
    "item_package_dimensions",
    "item_package_weight",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
]

PLUMBING_FIXTURE_VISIBLE_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "color",
    "material",
    "item_dimensions",
    "list_price_currency",
    "list_price",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_weight",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
]

PLUMBING_FIXTURE_REQUIRED_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "color",
    "material",
    "item_dimensions",
    "list_price_currency",
    "list_price",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_weight",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
]

PLUMBING_FIXTURE_SECTIONS: list[dict[str, Any]] = [
    {
        "keys": [
            "model_number",
            "model_name",
            "number_of_items",
            "color",
            "material",
        ],
    },
    {"title": "Item Dimensions(商品尺寸)", "panel": True, "keys": [
        "item_dimensions",
    ]},
    {"title": "List Price(不含税价目表)", "keys": ["list_price_currency", "list_price"]},
    {
        "title": "Item Package Dimensions(包装尺寸)",
        "panel": True,
        "keys": [
            "item_package_length",
            "item_package_width",
            "item_package_height",
        ],
    },
    {"title": "Package Weight(包裹重量)", "panel": True, "keys": ["item_package_weight"]},
    {
        "keys": [
            "country_of_origin",
            "supplier_declared_dg_hz_regulation",
        ],
    },
]


HARDWARE_TUBING_VISIBLE_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "color",
    "item_length_width",
    "list_price_currency",
    "list_price",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_weight",
    "unit_count",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
    "batteries_required",
]

HARDWARE_TUBING_REQUIRED_KEYS = [
    "model_number",
    "model_name",
    "number_of_items",
    "color",
    "item_length_width",
    "list_price_currency",
    "list_price",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_weight",
    "unit_count",
    "country_of_origin",
    "supplier_declared_dg_hz_regulation",
    "batteries_required",
]

HARDWARE_TUBING_SECTIONS: list[dict[str, Any]] = [
    {
        "keys": [
            "model_number",
            "model_name",
            "number_of_items",
            "color",
            "item_length_width",
        ],
    },
    {"title": "List Price(不含税价目表)", "keys": ["list_price_currency", "list_price"]},
    {
        "title": "Item Package Dimensions(包装尺寸)",
        "panel": True,
        "keys": [
            "item_package_length",
            "item_package_width",
            "item_package_height",
        ],
    },
    {"title": "Package Weight(包裹重量)", "panel": True, "keys": ["item_package_weight", "unit_count"]},
    {
        "keys": [
            "country_of_origin",
            "supplier_declared_dg_hz_regulation",
            "batteries_required",
        ],
    },
]

BABY_SECTIONS: list[dict[str, Any]] = [
    {
        "keys": [
            "model_number",
            "model_name",
            "number_of_items",
            "color",
            "material",
            "target_gender",
            "minimum_weight_recommendation",
            "maximum_weight_recommendation",
        ],
    },
    {"title": "List Price(不含税价目表)", "keys": ["list_price_currency", "list_price"]},
    {
        "title": "Item Package Dimensions(包装尺寸)",
        "panel": True,
        "keys": ["item_package_dimensions", "item_package_length", "item_package_width", "item_package_height"],
    },
    {"title": "Package Weight(包裹重量)", "panel": True, "keys": ["item_package_weight"]},
    {
        "keys": [
            "country_of_origin",
            "supplier_declared_dg_hz_regulation",
            "contains_liquid_contents",
            "is_assembly_required",
        ],
    },
]

LIST_PRICE_CURRENCY_OPTIONS = [
    {"value": "USD", "label": "USD(美元)"},
    {"value": "CAD", "label": "CAD(加元)"},
    {"value": "MXN", "label": "MXN(墨西哥比索)"},
]


FIELD_UI_OVERRIDES: dict[str, dict[str, Any]] = {
    "item_dimensions": {
        "type": "dimensions",
        "label_en": "Item Dimensions",
        "label_zh": "商品尺寸",
        "dimension_parts": ["length", "width", "height"],
        "unit_options": [
            {"value": "inches", "label": "Inches(英寸)"},
            {"value": "centimeters", "label": "Centimeters(厘米)"},
        ],
        "unit_default": "inches",
        "unit_key": "item_dimensions_unit",
    },
    "material": {
        "type": "select",
        "searchable": True,
        "options": [
            {"value": "ABS", "label": "ABS(丙烯腈丁二烯苯乙烯)"},
            {"value": "Brass", "label": "Brass(黄铜)"},
            {"value": "Stainless Steel", "label": "Stainless Steel(不锈钢)"},
            {"value": "Chrome", "label": "Chrome(镀铬)"},
            {"value": "Plastic", "label": "Plastic(塑料)"},
            {"value": "PVC", "label": "PVC(聚氯乙烯)"},
            {"value": "CPVC", "label": "CPVC(氯化聚氯乙烯)"},
            {"value": "Copper", "label": "Copper(铜)"},
            {"value": "Bronze", "label": "Bronze(青铜)"},
            {"value": "Zinc Alloy", "label": "Zinc Alloy(锌合金)"},
            {"value": "Aluminum", "label": "Aluminum(铝)"},
            {"value": "Cast Iron", "label": "Cast Iron(铸铁)"},
            {"value": "Galvanized Steel", "label": "Galvanized Steel(镀锌钢)"},
            {"value": "Rubber", "label": "Rubber(橡胶)"},
            {"value": "Silicone", "label": "Silicone(硅胶)"},
            {"value": "Ceramic", "label": "Ceramic(陶瓷)"},
            {"value": "Nickel", "label": "Nickel(镍)"},
        ],
    },
    "exterior_finish": {
        "type": "select",
        "searchable": True,
        "default": "machined",
        "options": [
            {"value": "brushed", "label": "Brushed(拉丝)"},
            {"value": "chrome", "label": "Chrome(铬)"},
            {"value": "machined", "label": "Machined(机加工)"},
            {"value": "milled", "label": "Milled(铣削)"},
            {"value": "painted", "label": "Painted(已涂漆)"},
            {"value": "polished", "label": "Polished(抛光)"},
        ],
    },
    "included_components": {
        "type": "checkbox_group",
        "layout": "inline",
        "editable_options": True,
        "allow_other": True,
        "options": [],
    },
    "is_assembly_required": {
        "label_en": "Required Assembly",
        "label_zh": "需要组装",
    },
    "warranty_description": {
        "type": "checkbox_group",
        "layout": "inline",
        "allow_other": True,
        "editable_options": True,
        "options": ["2 years"],
        "default": "2 years",
    },
    "batteries_required": {
        "type": "select",
        "default": "false",
        "options": [
            {"value": "false", "label": "No(否)"},
            {"value": "true", "label": "Yes(是)"},
        ],
    },
    "supplier_declared_dg_hz_regulation": {
        "type": "checkbox_group",
        "layout": "grid",
        "columns": 4,
        "option_labels": {
            "ghs": "GHS(全球统一制度)",
            "not_applicable": "Not Applicable(不适用)",
            "unknown": "Unknown(未知)",
            "other": "Other(其他)",
            "storage": "Storage(存储)",
            "transportation": "Transportation(运输)",
            "waste": "Waste(废物)",
        },
    },
}

PACKAGE_DIMENSION_PARTS = [
    ("item_package_length", "Item Package Length", "包装长度"),
    ("item_package_width", "Item Package Width", "包装宽度"),
    ("item_package_height", "Item Package Height", "包装高度"),
]

DIMENSION_PARENT_PARTS = {
    "item_package_dimensions": ["item_package_length", "item_package_width", "item_package_height"],
    "item_dimensions": ["item_length", "item_width", "item_height"],
}


def expand_required_dimension_keys(required_keys: set[str] | list[str]) -> set[str]:
    expanded = {str(key) for key in required_keys if key}
    for parent, parts in DIMENSION_PARENT_PARTS.items():
        if parent in expanded:
            expanded.update(parts)
            expanded.discard(parent)
    return expanded


def resolve_preset(product_type: str) -> dict[str, Any]:
    product_type = (product_type or "AUTO_PART").strip().upper()
    if product_type in AUTOMOTIVE_TYPES or product_type.endswith("_PART"):
        return {
            "product_type": product_type,
            "visible_keys": AUTOMOTIVE_VISIBLE_KEYS,
            "required_keys": AUTOMOTIVE_REQUIRED_KEYS,
            "sections": AUTOMOTIVE_SECTIONS,
        }
    if product_type == "HEADPHONES":
        return {
            "product_type": product_type,
            "visible_keys": HEADPHONES_VISIBLE_KEYS,
            "required_keys": HEADPHONES_REQUIRED_KEYS,
            "sections": HEADPHONES_SECTIONS,
        }
    if product_type == "BABY_PRODUCT":
        return {
            "product_type": product_type,
            "visible_keys": BABY_VISIBLE_KEYS,
            "required_keys": BABY_REQUIRED_KEYS,
            "sections": BABY_SECTIONS,
        }
    if product_type == "HARDWARE_TUBING":
        return {
            "product_type": product_type,
            "visible_keys": HARDWARE_TUBING_VISIBLE_KEYS,
            "required_keys": HARDWARE_TUBING_REQUIRED_KEYS,
            "sections": HARDWARE_TUBING_SECTIONS,
        }
    if product_type == "PLUMBING_FIXTURE":
        return {
            "product_type": product_type,
            "visible_keys": PLUMBING_FIXTURE_VISIBLE_KEYS,
            "required_keys": PLUMBING_FIXTURE_REQUIRED_KEYS,
            "sections": PLUMBING_FIXTURE_SECTIONS,
        }
    return {
        "product_type": product_type,
        "visible_keys": [
            "model_number",
            "model_name",
            "number_of_items",
            "list_price_currency",
            "list_price",
            "item_package_length",
            "item_package_width",
            "item_package_height",
            "item_package_weight",
            "country_of_origin",
            "supplier_declared_dg_hz_regulation",
        ],
        "required_keys": [
            "model_number",
            "model_name",
            "number_of_items",
            "list_price_currency",
            "list_price",
            "item_package_length",
            "item_package_width",
            "item_package_height",
            "item_package_weight",
            "country_of_origin",
            "supplier_declared_dg_hz_regulation",
        ],
        "sections": AUTOMOTIVE_SECTIONS,
    }


def _expand_package_dimensions(field: dict[str, Any]) -> list[dict[str, Any]]:
    if field.get("key") != "item_package_dimensions" or field.get("type") != "dimensions":
        return [field]

    unit_options = field.get("unit_options") or [
        {"value": "inches", "label": "Inches(英寸)"},
        {"value": "centimeters", "label": "Centimeters(厘米)"},
    ]
    unit_default = field.get("unit_default") or "inches"
    expanded: list[dict[str, Any]] = []
    for key, label_en, label_zh in PACKAGE_DIMENSION_PARTS:
        expanded.append(
            {
                **deepcopy(field),
                "key": key,
                "label_en": label_en,
                "label_zh": label_zh,
                "type": "unit",
                "unit_key": f"{key}_unit",
                "unit_options": unit_options,
                "unit_default": unit_default,
                "source_dimensions": "item_package_dimensions",
                "required": field.get("required"),
                "required_static": field.get("required_static"),
                "schema_required": field.get("schema_required"),
                "baseline_required": field.get("baseline_required"),
            }
        )
    return expanded


def _prepare_field_map(fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    field_map: dict[str, dict[str, Any]] = {}
    for field in fields:
        if field.get("type") == "subsection" or not field.get("key"):
            continue
        for expanded in _expand_package_dimensions(deepcopy(field)):
            key = str(expanded["key"])
            if key not in field_map:
                field_map[key] = expanded
    return field_map


def _inject_list_price_currency(field_map: dict[str, dict[str, Any]]) -> None:
    list_price = field_map.get("list_price")
    if not list_price or "list_price_currency" in field_map:
        return

    is_required = bool(list_price.get("required") or list_price.get("required_static"))
    field_map["list_price_currency"] = {
        "key": "list_price_currency",
        "label_en": "List Price Currency",
        "label_zh": "价目表货币",
        "type": "select",
        "required": is_required,
        "required_static": is_required,
        "default": "USD",
        "options": LIST_PRICE_CURRENCY_OPTIONS,
        "preset_visible": list_price.get("preset_visible", True),
        "advanced": list_price.get("advanced", False),
        "conditional": False,
        "hidden": False,
        "companion_of": "list_price",
    }
    list_price["has_currency"] = True
    list_price["currency_key"] = "list_price_currency"
    list_price["currency_default"] = "USD"


def _apply_field_overrides(field: dict[str, Any]) -> dict[str, Any]:
    overrides = FIELD_UI_OVERRIDES.get(str(field.get("key") or ""))
    if not overrides:
        return field
    merged = deepcopy(field)
    merged.update(deepcopy(overrides))
    if overrides.get("type") == "checkbox_group" and field.get("options"):
        merged.setdefault("options", field["options"])
    return merged


def apply_product_type_layout(
    fields: list[dict[str, Any]],
    product_type: str,
    *,
    baseline_required: set[str] | None = None,
) -> list[dict[str, Any]]:
    preset = resolve_preset(product_type)
    baseline_keys = expand_required_dimension_keys(baseline_required or set())
    field_map = _prepare_field_map(fields)
    _inject_list_price_currency(field_map)

    # For unknown product types, make ALL Schema-returned fields visible
    # so required fields like load_capacity are never hidden in "more attributes"
    is_unknown_type = product_type not in AUTOMOTIVE_TYPES and not product_type.endswith("_PART") and product_type not in {"HEADPHONES", "BABY_PRODUCT", "HARDWARE_TUBING", "PLUMBING_FIXTURE"}

    if is_unknown_type:
        visible_keys = set(field_map.keys())
        preferred_keys = {key for key, field in field_map.items() if field.get("schema_required") or field.get("required_static")}
    else:
        visible_keys = set(preset["visible_keys"])
        preferred_keys = set(preset.get("required_keys") or [])

    for key, field in field_map.items():
        field = _apply_field_overrides(field)
        schema_required = bool(field.get("schema_required") or field.get("required_static"))
        is_baseline = key in baseline_keys
        is_required = schema_required or is_baseline or key in preferred_keys
        is_visible = is_required or key in visible_keys

        field["required"] = is_required
        field["required_static"] = schema_required or is_baseline
        field["schema_required"] = schema_required
        field["baseline_required"] = is_baseline
        field["advanced"] = not is_visible
        field["preset_visible"] = is_visible
        field["conditional"] = bool(field.get("conditional_required")) and not is_baseline
        field["hidden"] = False
        field_map[key] = field

    # Inject virtual dimension fields (e.g., item_dimensions -> item_length + item_width + item_height)
    for parent_key, part_keys in DIMENSION_PARENT_PARTS.items():
        if parent_key not in visible_keys:
            continue
        if parent_key in field_map:
            continue
        # Check if all part keys exist in field_map
        part_fields = [field_map.get(pk) for pk in part_keys]
        if not all(part_fields):
            continue
        # Create virtual dimension field from the first part
        base_field = deepcopy(part_fields[0])
        base_field["key"] = parent_key
        base_field["type"] = "dimensions"
        base_field["label_en"] = parent_key.replace("_", " ").title()
        base_field["label_zh"] = "商品尺寸" if parent_key == "item_dimensions" else base_field.get("label_en")
        base_field["dimension_parts"] = [pk.replace(f"{parent_key}_", "") for pk in part_keys] if parent_key != "item_dimensions" else ["length", "width", "height"]
        base_field["unit_options"] = [
            {"value": "inches", "label": "Inches(英寸)"},
            {"value": "centimeters", "label": "Centimeters(厘米)"},
        ]
        base_field["unit_default"] = "inches"
        base_field["unit_key"] = f"{parent_key}_unit"
        base_field["required"] = any(f.get("required") for f in part_fields)
        base_field["required_static"] = any(f.get("required_static") for f in part_fields)
        base_field["schema_required"] = any(f.get("schema_required") for f in part_fields)
        base_field["advanced"] = False
        base_field["preset_visible"] = True
        field_map[parent_key] = base_field
        # Hide original part fields
        for pk in part_keys:
            if pk in field_map:
                field_map[pk]["hidden"] = True

    ordered: list[dict[str, Any]] = []
    used: set[str] = set()

    def append_section(section_fields: list[dict[str, Any]], title: str = "", panel: bool = False) -> None:
        if not section_fields:
            return
        if title:
            ordered.append({"type": "subsection", "title": title, "panel": panel})
        ordered.extend(section_fields)

    for section in preset["sections"]:
        section_fields: list[dict[str, Any]] = []
        for key in section.get("keys", []):
            field = field_map.get(key)
            if field is None or key in used:
                continue
            section_fields.append(field)
            used.add(key)
        append_section(section_fields, str(section.get("title") or "").strip(), bool(section.get("panel")))

    # For unknown product types, don't use preset sections at all —
    # group required fields first, then remaining.
    if is_unknown_type and not used:
        required_fields = [
            field_map[key]
            for key in sorted(field_map.keys(), key=lambda k: str(field_map[k].get("label_en") or k))
            if key not in used and field_map[key].get("required")
        ]
        if required_fields:
            append_section(required_fields, "亚马逊必填属性")
            used.update(f["key"] for f in required_fields if f.get("key"))

    required_remaining = [
        field_map[key]
        for key in sorted(field_map.keys(), key=lambda item: str(field_map[item].get("label_en") or item))
        if key not in used and field_map[key].get("required")
    ]
    if required_remaining:
        append_section(required_remaining, "亚马逊必填属性")
        used.update(field["key"] for field in required_remaining if field.get("key"))

    remaining = [
        field_map[key]
        for key in sorted(field_map.keys(), key=lambda item: str(field_map[item].get("label_en") or item))
        if key not in used
    ]
    if remaining:
        if is_unknown_type:
            append_section(remaining, "更多属性")
        else:
            ordered.append({"type": "subsection", "title": "更多属性", "advanced": True})
            ordered.extend(remaining)
    return ordered


def summarize_required_fields(fields: list[dict[str, Any]]) -> dict[str, Any]:
    visible_required = [
        field
        for field in fields
        if field.get("type") != "subsection" and field.get("required")
    ]
    return {
        "required_count": len(visible_required),
        "required_keys": [field["key"] for field in visible_required],
        "required_labels": {
            field["key"]: field.get("label_zh") or field.get("label_en") or field["key"]
            for field in visible_required
        },
    }
