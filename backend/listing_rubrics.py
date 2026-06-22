"""Category-specific listing quality rubrics for AI soft scoring."""
from __future__ import annotations

from typing import Any

from attribute_presets import AUTOMOTIVE_TYPES, resolve_preset

# Keys commonly useful for rubric-aware AI scoring (from attribute_presets layouts)
RUBRIC_ATTRIBUTE_KEYS = (
    "part_number",
    "model_number",
    "model_name",
    "automotive_fit_type",
    "included_components",
    "item_package_length",
    "item_package_width",
    "item_package_height",
    "item_package_dimensions",
    "item_package_weight",
    "material",
    "color",
    "headphones_form_factor",
    "headphones_ear_placement",
    "connectivity_technology",
    "noise_control",
    "exterior_finish",
    "number_of_items",
)

RUBRIC_GROUPS: dict[str, dict[str, Any]] = {
    "automotive": {
        "label": "汽配 / 汽配周边",
        "match": lambda pt: pt in AUTOMOTIVE_TYPES or pt.endswith("_PART"),
        "focus": (
            "Bullets/描述是否覆盖车型兼容 fitment、Part Number / OE 号、安装位置、"
            "材质与耐用性；标题是否含核心零件词而非泛称。"
        ),
        "bullet_must_cover": (
            "compatibility/fitment（适用车型或 fit type）",
            "part number 或 OE 参照",
            "材质/规格/安装要点",
        ),
        "attribute_hints": ("part_number", "automotive_fit_type", "model_number", "included_components"),
    },
    "home_hardware": {
        "label": "家居 / 五金 / 管材",
        "match": lambda pt: pt in {"HARDWARE_TUBING", "PLUMBING_FIXTURE", "HOME", "HOME_IMPROVEMENT"},
        "focus": (
            "是否明确尺寸 dimensions、材质 material、接口规格、包装内含与使用场景；"
            "Bullets 应量化规格而非空泛形容词。"
        ),
        "bullet_must_cover": ("尺寸/规格", "材质", "适用场景或安装方式"),
        "attribute_hints": (
            "item_package_dimensions",
            "item_package_length",
            "item_package_width",
            "item_package_height",
            "material",
            "number_of_items",
        ),
    },
    "electronics": {
        "label": "电子 / 耳机",
        "match": lambda pt: pt in {"HEADPHONES", "ELECTRONICS", "CONSUMER_ELECTRONICS"} or "HEADPHONE" in pt,
        "focus": (
            "是否覆盖连接方式、兼容性、续航/规格、适用设备、包装清单；"
            "避免与 Amazon 政策冲突的绝对化性能宣称。"
        ),
        "bullet_must_cover": ("核心规格/连接方式", "兼容性/适用设备", "包装与保修要点"),
        "attribute_hints": (
            "connectivity_technology",
            "headphones_form_factor",
            "headphones_ear_placement",
            "noise_control",
            "model_number",
        ),
    },
    "baby": {
        "label": "母婴",
        "match": lambda pt: pt == "BABY_PRODUCT" or pt.startswith("BABY_"),
        "focus": "安全认证、适用年龄、材质、清洗方式、尺寸是否在文案中清晰体现。",
        "bullet_must_cover": ("安全/认证", "适用年龄或规格", "材质与护理"),
        "attribute_hints": ("material", "number_of_items", "item_package_dimensions"),
    },
}


def _resolve_group(product_type: str) -> str:
    pt = (product_type or "").strip().upper()
    for key, group in RUBRIC_GROUPS.items():
        if group["match"](pt):
            return key
    return "general"


def extract_rubric_attributes(data: dict[str, Any]) -> dict[str, str]:
    """Pull attribute fields from flat payload or nested attributes dict."""
    raw = data.get("attributes")
    if isinstance(raw, dict):
        source = raw
    else:
        source = data
    out: dict[str, str] = {}
    for key in RUBRIC_ATTRIBUTE_KEYS:
        val = source.get(key)
        if val is None or val == "":
            continue
        text = str(val).strip()
        if text:
            out[key] = text
    return out


def build_category_rubric_block(data: dict[str, Any]) -> str:
    """Build rubric text injected into AI scorer prompt."""
    product_type = str(
        data.get("product_type") or data.get("category") or ""
    ).strip().upper()
    category_path = str(data.get("category_path") or "").strip()
    group_key = _resolve_group(product_type)
    group = RUBRIC_GROUPS.get(group_key)

    if group:
        label = group["label"]
        focus = group["focus"]
        must_cover = "、".join(group["bullet_must_cover"])
    else:
        label = "通用类目"
        focus = "卖点是否具体、可验证，规格与使用场景是否写清。"
        must_cover = "核心规格、使用场景、包装/售后"

    preset = resolve_preset(product_type or "AUTO_PART")
    required = preset.get("required_keys") or []
    required_preview = ", ".join(required[:12])
    if len(required) > 12:
        required_preview += f" …(+{len(required) - 12})"

    attrs = extract_rubric_attributes(data)
    attr_lines = [f"  - {k}: {v}" for k, v in attrs.items()] or ["  (none provided)"]

    lines = [
        f"Category rubric ({label}):",
        f"- Product type: {product_type or 'N/A'}",
        f"- Browse path: {category_path or 'N/A'}",
        f"- Preset required attributes (schema): {required_preview or 'N/A'}",
        f"- Rubric focus: {focus}",
        f"- Bullets should cover: {must_cover}",
        "- Provided attribute values:",
        *attr_lines,
        "Apply this rubric when scoring bullets/description/compliance soft quality.",
    ]
    return "\n".join(lines)
