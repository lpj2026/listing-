"""Listing Generator (multi-plan) & Scorer (detailed diagnostic)."""
from __future__ import annotations

from typing import Any

from ai_service import _chat, extract_json

# ── Generator ─────────────────────────────────────────────────────

GENERATOR_SYSTEM = """You are a senior Amazon copywriting strategist. Your job is to analyze the product data provided and generate 2-3 distinct listing plans, each with a different market positioning strategy.

For each plan you MUST include:
1. "strategy": the marketing angle (e.g. "专业性能型", "性价比实用型", "高端品质型")
2. "reasoning": WHY this strategy works for this product — 2-3 sentences in Chinese explaining the logic
3. "buyer_profile": who this plan targets, in Chinese
4. "expected_benefit": what conversion/CTR improvement to expect, in Chinese
5. "title": full Amazon title in English, 150-200 characters
6. "bullets": exactly 5 bullet points in English, each 80-250 chars, with category-relevant prefixes like [PREMIUM QUALITY], [PERFECT FIT], [EASY INSTALLATION], etc.
7. "description": HTML-formatted product description in English with <b> headers and <ul> lists
8. "search_terms": space-separated keywords, max 250 chars, NOT repeating title words

Output ONLY valid JSON, no markdown fences:
{
  "plans": [
    {
      "strategy": "...",
      "reasoning": "...",
      "buyer_profile": "...",
      "expected_benefit": "...",
      "title": "...",
      "bullets": ["...","...","...","...","..."],
      "description": "...",
      "search_terms": "..."
    }
  ]
}"""


def generate_plans(data: dict[str, Any]) -> dict[str, Any]:
    """Generate 2-3 listing plans from structured product data."""
    product_name = str(data.get("product_name", "")).strip()
    if not product_name:
        raise ValueError("product_name 不能为空")

    user_prompt_parts = [f"Product: {product_name}"]

    category = str(data.get("category", ""))
    if category:
        user_prompt_parts.append(f"Category: {category}")

    price = data.get("price")
    if price:
        user_prompt_parts.append(f"Target Price: ${price}")

    material = str(data.get("material", ""))
    process = str(data.get("process", ""))
    if material or process:
        user_prompt_parts.append(f"Material & Process: {material} / {process}")

    specs = []
    for key in ("spec1_name", "spec2_name"):
        name = str(data.get(key, ""))
        if name:
            val = str(data.get(key.replace("name", "value"), ""))
            specs.append(f"{name}: {val}")
    if specs:
        user_prompt_parts.append("Key Specs: " + "; ".join(specs))

    differentiator = str(data.get("differentiator", ""))
    if differentiator:
        user_prompt_parts.append(f"Key Differentiator: {differentiator}")

    audience = str(data.get("audience", ""))
    if audience:
        user_prompt_parts.append(f"Target Audience: {audience}")

    competitor_asin = str(data.get("competitor_asin", ""))
    if competitor_asin:
        user_prompt_parts.append(f"Competitor ASIN: {competitor_asin}")

    positionings = data.get("positioning", [])
    if positionings and isinstance(positionings, list):
        user_prompt_parts.append(f"Desired Positionings: {', '.join(positionings)}")

    user_prompt = "\n".join(user_prompt_parts)
    user_prompt += "\n\nGenerate 2-3 listing plans based on this product data."

    messages = [
        {"role": "system", "content": GENERATOR_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    raw = _chat(messages, temperature=0.8, max_tokens=4096)
    result = extract_json(raw)

    plans = result.get("plans", [])
    if not plans:
        raise RuntimeError("AI 未返回任何方案")
    for plan in plans:
        bullets = plan.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = []
        while len(bullets) < 5:
            bullets.append("")
        plan["bullets"] = bullets[:5]
        plan.setdefault("strategy", "通用方案")
        plan.setdefault("reasoning", "")
        plan.setdefault("buyer_profile", "")
        plan.setdefault("expected_benefit", "")

    return {"plans": plans, "plan_count": len(plans)}


# ── Scorer ────────────────────────────────────────────────────────

SCORER_SYSTEM = """You are an Amazon listing quality auditor with deep knowledge of A9 algorithm ranking factors and buyer psychology. Your task is to perform a detailed diagnostic on the provided listing.

Score and diagnose these dimensions (each 0-25 points, total 100):
1. 标题质量 (Title Quality): keyword placement, length 150-200 ideal, brand inclusion, readability, search match
2. Bullet Points: count (5 optimal), benefit-driven language, uniqueness, keyword coverage, persuasive power
3. 描述质量 (Description Quality): HTML formatting, completeness, keyword reinforcement, trust-building elements
4. 关键词与搜索 (Keywords & Search): search terms optimization, title-keyword distinction, density
5. 合规与展示 (Compliance & Presentation): prohibited words, image sufficiency, price signals

For EACH issue found, provide:
- "issue": what's wrong (Chinese)
- "why_matters": why this matters to ranking/conversion (Chinese, explain the Amazon mechanism)
- "how_to_fix": specific actionable fix (Chinese)
- "expected_gain": estimated improvement after fixing (Chinese, e.g. "预计搜索曝光提升15-20%")

For each dimension, also list what's done well ("positives").

Output ONLY valid JSON:
{
  "overall_score": 68,
  "overall_grade": "良好",
  "overall_summary": "整体评价...",
  "dimensions": {
    "title": {
      "score": 18, "max": 25,
      "positives": ["长度合理", "..."],
      "issues": [
        {"issue": "...", "why_matters": "...", "how_to_fix": "...", "expected_gain": "..."}
      ]
    },
    "bullets": { ... },
    "description": { ... },
    "keywords": { ... },
    "compliance": { ... }
  },
  "top_priority": ["最紧急的1-3条建议"]
}"""


def score_listing(data: dict[str, Any]) -> dict[str, Any]:
    """Detailed AI-powered listing diagnostic."""
    title = str(data.get("title", "")).strip()
    if not title:
        raise ValueError("title 不能为空")

    bullets = data.get("bullets") or []
    if isinstance(bullets, list):
        bullets_text = "\n".join(f"{i+1}. {b}" for i, b in enumerate(bullets) if b and str(b).strip())
    else:
        bullets_text = ""

    user_prompt = f"""Diagnose this Amazon listing:

Title: {title}
Bullet Points:
{bullets_text or "(none)"}
Description: {str(data.get('description', '')).strip() or '(none)'}
Search Terms: {str(data.get('search_terms', '')).strip() or '(none)'}
Image Count: {data.get('image_count', 0)}
Price: ${data.get('price') if data.get('price') else 'N/A'}
Category: {str(data.get('category', '')).strip() or 'N/A'}

Provide detailed diagnostic in Chinese, following the JSON format exactly."""

    messages = [
        {"role": "system", "content": SCORER_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    raw = _chat(messages, temperature=0.3, max_tokens=4096)
    result = extract_json(raw)

    result.setdefault("overall_score", 0)
    result.setdefault("overall_grade", "需优化")
    result.setdefault("overall_summary", "")
    result.setdefault("top_priority", [])
    for dim_key in ("title", "bullets", "description", "keywords", "compliance"):
        if dim_key not in result.get("dimensions", {}):
            result.setdefault("dimensions", {})[dim_key] = {
                "score": 0, "max": 25, "positives": [], "issues": []
            }
    return result


# ── Combined: Score + Targeted Optimization ─────────────────────────

OPTIMIZE_SYSTEM = """You are an Amazon listing optimization strategist. You receive a product's current listing content AND its scoring diagnostic. Your job is to generate targeted improvement suggestions for each weakness found in the scoring, and also produce 1-2 optimized versions of the listing.

For each major issue identified in the scoring:
1. Explain WHY this needs to be fixed (Amazon algorithm + buyer psychology)
2. What BENEFIT the fix brings (search ranking, CTR, conversion rate, etc.)
3. Provide the optimized version

Output ONLY valid JSON:
{
  "optimizations": [
    {
      "target": "title / bullets / description / keywords / compliance",
      "issue_summary": "当前问题简述",
      "why_optimize": "为什么必须优化（算法+买家心理角度）",
      "expected_benefit": "优化后的预期效果",
      "optimized_content": "优化后的文案"
    }
  ],
  "optimized_listing": {
    "title": "...",
    "bullets": ["...","...","...","...","..."],
    "description": "...",
    "search_terms": "..."
  },
  "overall_strategy": "整体优化策略说明"
}"""


def optimize_listing(listing_data: dict[str, Any], scoring_result: dict[str, Any]) -> dict[str, Any]:
    """Generate targeted optimizations based on scoring weaknesses."""
    user_prompt = f"""Current Listing:
Title: {str(listing_data.get('title', ''))}
Bullets: {chr(10).join(str(b) for b in (listing_data.get('bullets') or []) if b)}
Description: {str(listing_data.get('description', ''))}
Search Terms: {str(listing_data.get('search_terms', ''))}
Category: {str(listing_data.get('category', ''))}

Scoring Results:
Overall Score: {scoring_result.get('overall_score', 'N/A')}/100
Grade: {scoring_result.get('overall_grade', 'N/A')}

Dimensions:
{_format_dimensions_for_prompt(scoring_result.get('dimensions', {}))}

Based on the above scoring, generate targeted optimizations for each weakness. Focus on WHY each fix matters and WHAT benefit it brings."""

    messages = [
        {"role": "system", "content": OPTIMIZE_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    raw = _chat(messages, temperature=0.7, max_tokens=4096)
    result = extract_json(raw)
    result.setdefault("optimizations", [])
    result.setdefault("optimized_listing", {})
    result.setdefault("overall_strategy", "")
    return result


def _format_dimensions_for_prompt(dims: dict) -> str:
    lines = []
    for key, dim in dims.items():
        score = dim.get("score", 0)
        max_s = dim.get("max", 25)
        issues = dim.get("issues", [])
        issue_texts = [f"  - {i.get('issue', '')}" for i in issues[:3]]
        lines.append(f"{key}: {score}/{max_s}\n" + "\n".join(issue_texts))
    return "\n".join(lines)
