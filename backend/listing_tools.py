"""Listing Scorer & Optimizer (score → optimize → rescore loop)."""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any

from ai_service import chat_json
from listing_rubrics import build_category_rubric_block, extract_rubric_attributes
from listing_rules import compute_rule_score, format_rules_for_prompt, merge_rule_and_ai_scores
from listing_score_model import DIM_KEYS
from publish_readiness import check_publish_readiness

_RULE_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
_RULE_CACHE_MAX = 128
AI_SCORE_TEMPERATURE = 0.1
OPTIMIZE_TEMPERATURE = 0.45
RESCORE_TARGET = 75

_DIM_LABELS = {
    "title": "标题",
    "bullets": "Bullet Points",
    "description": "描述",
    "keywords": "Search Terms / 关键词",
    "compliance": "合规与展示",
}

_DIM_CRITERIA = {
    "title": "关键词策略、可读性、搜索意图（不含长度/品牌/格式）",
    "bullets": "利益导向文案、说服力、关键词覆盖（不含条数/长度/重复/emoji）",
    "description": "叙事、信任感、关键词 reinforcement（不含 HTML 长度）",
    "keywords": "搜索词策略、同义词、长尾意图（不含格式/重复/与标题重叠）",
    "compliance": "呈现质量（不含图片数/违禁词/emoji）",
}

_DIM_SYSTEM = """You are an Amazon listing quality auditor scoring ONE dimension only (soft quality).
Hard rule checks are already done — do NOT re-report length limits, brand, emoji, prohibited words, or counts.

Return JSON only:
{"score": 0, "positives": ["..."], "issues": [{"issue":"...","why_matters":"...","how_to_fix":"...","expected_gain":"..."}], "note": "一句中文小结"}"""

OPTIMIZE_SYSTEM = """You are an Amazon listing optimization expert. Fix EVERY issue in the diagnostic.

CRITICAL:
- optimized_content = ACTUAL rewritten copy, not suggestions
- optimized_listing must incorporate ALL fixes
- Title 150-200 chars, include brand; Bullets exactly 5, 80-250 chars each, [PREFIX] format, no emoji
- Description HTML 500+ chars; Search terms ≤250, lowercase, space-separated
- NO prohibited words: best, #1, guaranteed, miracle, etc.

Return JSON:
{"optimizations": [{"target":"title","original_text":"...","issue_summary":"...","why_optimize":"...","expected_benefit":"...","optimized_content":"..."}], "optimized_listing": {"title":"...","bullets":["..."],"description":"...","search_terms":"..."}, "overall_strategy": "..."}"""

_RETRY_SYSTEM = """Fix ONLY the listed rule failures in this listing. Return JSON:
{"optimized_listing": {"title":"...","bullets":["..."],"description":"...","search_terms":"..."}}"""


def score_listing(
    data: dict[str, Any],
    *,
    skip_ai: bool = False,
    previous_result: dict[str, Any] | None = None,
    rescore_mode: bool = False,
) -> dict[str, Any]:
    """Rule + AI hybrid listing diagnostic."""
    payload = _normalize_score_payload(data)
    if not payload["title"]:
        raise ValueError("title 不能为空")

    rule_result, rule_cached = _get_rule_score(payload)
    publish_ready = check_publish_readiness(payload)

    if skip_ai:
        merged = merge_rule_and_ai_scores(rule_result, {"dimensions": {}, "overall_summary": "", "top_priority": []})
        merged["overall_summary"] = "规则评分（未调用 AI）"
        merged["rule_cached"] = rule_cached
        merged["publish_readiness"] = publish_ready
        return merged

    changed_dims = _detect_changed_dims(previous_result, payload) if rescore_mode and previous_result else set(DIM_KEYS)
    confirm_meta = None

    if rescore_mode and previous_result and changed_dims != set(DIM_KEYS):
        ai_result = _score_ai_partial(payload, rule_result, previous_result, changed_dims)
        merged = merge_rule_and_ai_scores(rule_result, ai_result)
        merged["rescore_partial"] = True
        merged["rescore_dims_scored"] = sorted(changed_dims)
    elif payload.get("ai_confirm"):
        ai_result = _score_ai_per_dimension(payload, rule_result, confirm=True)
        confirm_meta = ai_result.pop("_confirm_meta", None)
        merged = merge_rule_and_ai_scores(rule_result, ai_result)
    else:
        ai_result = _score_ai_per_dimension(payload, rule_result)
        merged = merge_rule_and_ai_scores(rule_result, ai_result)

    merged["ai_raw_dimensions"] = ai_result.get("dimensions") or {}
    merged["ai_scoring_mode"] = "per_dimension"
    merged["rule_cached"] = rule_cached
    merged["publish_readiness"] = publish_ready
    merged["ai_score_normalized"] = True
    merged["_listing_payload"] = {
        "title": payload["title"],
        "bullets": payload.get("bullets"),
        "description": payload.get("description"),
        "search_terms": payload.get("search_terms"),
    }
    if confirm_meta:
        merged["ai_confirm"] = confirm_meta

    if publish_ready.get("score", 100) < 80:
        note = f"刊登就绪度 {publish_ready.get('score')}/100 — 评分高不代表可刊登，请查看就绪度清单"
        merged["overall_summary"] = f"{merged.get('overall_summary', '')} {note}".strip()

    return merged


def _normalize_score_payload(data: dict[str, Any]) -> dict[str, Any]:
    product_type = str(data.get("product_type") or data.get("category") or "").strip()
    category_path = str(data.get("category_path") or data.get("category_name") or "").strip()
    brand = str(data.get("brand") or "").strip()
    manufacturer = str(data.get("manufacturer") or brand).strip()

    bullets_raw = data.get("bullets") or []
    bullets = [str(b).strip() for b in bullets_raw if b and str(b).strip()] if isinstance(bullets_raw, list) else []

    raw_img = data.get("image_count")
    image_count: int | None
    if raw_img is None or raw_img == "":
        image_count = None
    else:
        try:
            image_count = int(raw_img)
        except (TypeError, ValueError):
            image_count = None

    out: dict[str, Any] = {
        "title": str(data.get("title", "")).strip(),
        "bullets": bullets,
        "description": str(data.get("description", "")).strip(),
        "search_terms": str(data.get("search_terms", "")).strip(),
        "image_count": image_count,
        "images_linked": bool(data.get("images_linked")),
        "price": data.get("price"),
        "product_type": product_type,
        "category": product_type,
        "category_path": category_path,
        "brand": brand,
        "manufacturer": manufacturer,
        "msku": str(data.get("msku") or data.get("seller_sku") or data.get("parent_sku") or "").strip(),
        "upc_exemption": str(data.get("upc_exemption") or "").strip(),
        "external_product_id": str(data.get("external_product_id") or data.get("upc") or "").strip(),
        "attributes": extract_rubric_attributes(data),
        "ai_confirm": bool(data.get("ai_confirm")),
        "product_images": data.get("product_images"),
    }
    for key, val in data.items():
        if key not in out and val is not None and str(val).strip():
            out[key] = val
    return out


def _rule_cache_key(payload: dict[str, Any]) -> str:
    cache_payload = {k: payload[k] for k in (
        "title", "bullets", "description", "search_terms",
        "image_count", "images_linked", "brand", "manufacturer",
    ) if k in payload}
    return hashlib.sha256(json.dumps(cache_payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _get_rule_score(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    key = _rule_cache_key(payload)
    if key in _RULE_CACHE:
        _RULE_CACHE.move_to_end(key)
        return _RULE_CACHE[key], True
    result = compute_rule_score(payload)
    _RULE_CACHE[key] = result
    if len(_RULE_CACHE) > _RULE_CACHE_MAX:
        _RULE_CACHE.popitem(last=False)
    return result, False


def _listing_context_block(payload: dict[str, Any]) -> str:
    bullets = payload.get("bullets") or []
    bullets_text = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(bullets) if b)
    img = payload.get("image_count")
    img_text = str(img) if img is not None else "unknown"
    attrs = payload.get("attributes") or {}
    attr_block = "\n".join(f"  {k}: {v}" for k, v in attrs.items()) or "  (none)"
    return f"""Brand: {payload.get('brand') or 'N/A'}
Manufacturer: {payload.get('manufacturer') or 'N/A'}
Product type: {payload.get('product_type') or 'N/A'}
Category path: {payload.get('category_path') or 'N/A'}
Price: ${payload.get('price') if payload.get('price') else 'N/A'}
Images: {img_text}
Attributes:
{attr_block}

Title: {payload['title']}
Bullets:
{bullets_text or '(none)'}
Description: {payload.get('description') or '(none)'}
Search Terms: {payload.get('search_terms') or '(none)'}"""


def _dim_content_for(dim: str, payload: dict[str, Any]) -> str:
    if dim == "title":
        return f"Title to score:\n{payload['title']}"
    if dim == "bullets":
        bullets = payload.get("bullets") or []
        text = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(bullets) if b)
        return f"Bullet Points to score:\n{text or '(none)'}"
    if dim == "description":
        return f"Description to score:\n{payload.get('description') or '(none)'}"
    if dim == "keywords":
        return f"Search Terms to score:\n{payload.get('search_terms') or '(none)'}"
    return _listing_context_block(payload) + "\n\nScore overall presentation quality for this listing."


def _score_one_dimension(dim: str, payload: dict[str, Any], rule_result: dict[str, Any]) -> dict[str, Any]:
    rubric = build_category_rubric_block(payload) if dim in {"bullets", "description", "compliance"} else ""
    user = f"""Score dimension: {_DIM_LABELS[dim]} ({dim})
Criteria: {_DIM_CRITERIA[dim]}

{_dim_content_for(dim, payload)}

{f'Category rubric:{chr(10)}{rubric}' if rubric else ''}

Relevant rule checks (do NOT re-score these):
{format_rules_for_prompt(rule_result)}

Score 0-10 integer. Issues in Chinese."""

    raw = chat_json(
        [{"role": "system", "content": _DIM_SYSTEM}, {"role": "user", "content": user}],
        temperature=AI_SCORE_TEMPERATURE,
        max_tokens=1536,
    )
    return _normalize_dim_ai(raw, dim)


def _normalize_dim_ai(raw: dict[str, Any], dim: str) -> dict[str, Any]:
    score = _clamp_score(raw.get("score", 0))
    issues = [i for i in (raw.get("issues") or []) if isinstance(i, dict)]
    positives = [str(p) for p in (raw.get("positives") or []) if p]
    return {"score": score, "max": 10, "positives": positives, "issues": issues, "note": str(raw.get("note") or "").strip()}


def _score_ai_per_dimension(payload: dict[str, Any], rule_result: dict[str, Any], *, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return _assemble_ai_from_dims({dim: _score_one_dimension(dim, payload, rule_result) for dim in DIM_KEYS})

    runs = [{dim: _score_one_dimension(dim, payload, rule_result) for dim in DIM_KEYS} for _ in range(2)]
    merged_dims: dict[str, Any] = {}
    per_dim = []
    for dim in DIM_KEYS:
        s1, s2 = runs[0][dim]["score"], runs[1][dim]["score"]
        avg = int((s1 + s2) / 2)
        issues: list[dict] = []
        seen: set[str] = set()
        for run in runs:
            for issue in run[dim].get("issues") or []:
                sig = str(issue.get("issue", "")).strip()
                if sig and sig not in seen:
                    seen.add(sig)
                    issues.append(dict(issue))
        positives = list(dict.fromkeys(runs[0][dim]["positives"] + runs[1][dim]["positives"]))
        merged_dims[dim] = {"score": avg, "max": 10, "positives": positives, "issues": issues, "note": runs[0][dim].get("note", "")}
        per_dim.append({"dimension": dim, "run1": s1, "run2": s2, "averaged": avg})

    result = _assemble_ai_from_dims(merged_dims)
    result["_confirm_meta"] = {"runs": 2, "per_dimension": per_dim}
    return result


def _assemble_ai_from_dims(dims: dict[str, dict[str, Any]]) -> dict[str, Any]:
    notes = [dims[d].get("note", "") for d in DIM_KEYS if dims.get(d, {}).get("note")]
    priorities: list[str] = []
    for dim in DIM_KEYS:
        for issue in dims.get(dim, {}).get("issues") or []:
            text = str(issue.get("issue", "")).strip()
            if text:
                priorities.append(text)
    return {
        "overall_score": sum(dims[d]["score"] for d in DIM_KEYS),
        "overall_summary": "；".join(n for n in notes if n) or "分维度 AI 软质量评估完成",
        "dimensions": dims,
        "top_priority": priorities[:3],
    }


def _score_ai_partial(payload: dict[str, Any], rule_result: dict[str, Any], previous: dict[str, Any], changed_dims: set[str]) -> dict[str, Any]:
    prev_raw = previous.get("ai_raw_dimensions") or {}
    dims: dict[str, Any] = {}
    for dim in DIM_KEYS:
        if dim in changed_dims or dim not in prev_raw:
            dims[dim] = _score_one_dimension(dim, payload, rule_result)
        else:
            dims[dim] = dict(prev_raw[dim])
    return _assemble_ai_from_dims(dims)


def _detect_changed_dims(previous: dict[str, Any], payload: dict[str, Any]) -> set[str]:
    prev_data = previous.get("_listing_payload") or {}
    changed: set[str] = set()
    if str(prev_data.get("title", "")) != payload["title"]:
        changed.add("title")
    if list(prev_data.get("bullets") or []) != list(payload.get("bullets") or []):
        changed.add("bullets")
    if str(prev_data.get("description", "")) != str(payload.get("description", "")):
        changed.add("description")
    if str(prev_data.get("search_terms", "")) != str(payload.get("search_terms", "")):
        changed.add("keywords")
    return changed or set(DIM_KEYS)


def _clamp_score(value: Any) -> int:
    try:
        return max(0, min(10, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def optimize_listing(listing_data: dict[str, Any], scoring_result: dict[str, Any]) -> dict[str, Any]:
    listing_data = _normalize_score_payload(listing_data)
    before_score = int(scoring_result.get("overall_score") or 0)

    user_prompt = f"""Current Listing:
{_listing_context_block(listing_data)}

Scoring: {before_score}/100 · {scoring_result.get('overall_grade', '')}
Failed rules: {_failed_rule_summary(scoring_result)}

Dimensions:
{_format_dimensions_for_prompt(scoring_result.get('dimensions', {}))}

Address EVERY issue. Target rescore ≥ {RESCORE_TARGET}/100."""

    result = chat_json(
        [{"role": "system", "content": OPTIMIZE_SYSTEM}, {"role": "user", "content": user_prompt}],
        temperature=OPTIMIZE_TEMPERATURE,
        max_tokens=4096,
    )
    result.setdefault("optimizations", [])
    result.setdefault("optimized_listing", {})
    result.setdefault("overall_strategy", "")

    ol = _sanitize_optimized_listing(result.get("optimized_listing") or {})
    result["optimized_listing"] = ol

    for opt in result.get("optimizations") or []:
        if isinstance(opt.get("optimized_content"), list):
            opt["optimized_content"] = "\n".join(str(x) for x in opt["optimized_content"])

    scoring_result = dict(scoring_result)
    scoring_result["_listing_payload"] = {
        "title": listing_data["title"],
        "bullets": listing_data.get("bullets"),
        "description": listing_data.get("description"),
        "search_terms": listing_data.get("search_terms"),
    }

    rescore_payload = _build_rescore_payload(listing_data, ol)
    rescore_result = score_listing(rescore_payload, previous_result=scoring_result, rescore_mode=True)
    after_score = int(rescore_result.get("overall_score") or 0)

    if after_score < RESCORE_TARGET:
        failed = [c for c in rescore_result.get("rule_checks") or [] if not c.get("passed") and not c.get("skipped")]
        if failed:
            ol = _retry_failed_rules(ol, failed)
            rescore_payload = _build_rescore_payload(listing_data, ol)
            retry_result = score_listing(rescore_payload, previous_result=rescore_result, rescore_mode=True)
            if int(retry_result.get("overall_score") or 0) >= after_score:
                rescore_result = retry_result
                result["optimized_listing"] = ol
                after_score = int(rescore_result.get("overall_score") or 0)
                result["retry_for_rules"] = True

    result["score_comparison"] = {
        "original_score": before_score,
        "verified_new_score": after_score,
        "score_delta": after_score - before_score,
        "original_grade": scoring_result.get("overall_grade", ""),
        "verified_grade": rescore_result.get("overall_grade", ""),
        "why_improved": _summarize_score_delta(before_score, after_score, scoring_result, rescore_result),
        "estimated_new_score": after_score,
        "target_met": after_score >= RESCORE_TARGET,
    }
    result["rescore"] = rescore_result
    result["loop_complete"] = True
    return result


def _failed_rule_summary(scoring_result: dict[str, Any]) -> str:
    failed = [c for c in scoring_result.get("rule_checks") or [] if not c.get("passed") and not c.get("skipped")]
    return "(none)" if not failed else "; ".join(f"{c.get('id')}: {str(c.get('message', ''))[:60]}" for c in failed[:8])


def _retry_failed_rules(listing: dict[str, Any], failed_rules: list[dict[str, Any]]) -> dict[str, Any]:
    fixes = "\n".join(f"- {c.get('id')}: {c.get('message')}" for c in failed_rules if c.get("message"))
    prompt = f"""Listing:
Title: {listing.get('title', '')}
Bullets: {json.dumps(listing.get('bullets') or [], ensure_ascii=False)}
Description: {str(listing.get('description', ''))[:800]}
Search Terms: {listing.get('search_terms', '')}

Fix ONLY these rule failures:
{fixes}"""
    try:
        raw = chat_json(
            [{"role": "system", "content": _RETRY_SYSTEM}, {"role": "user", "content": prompt}],
            temperature=OPTIMIZE_TEMPERATURE,
            max_tokens=4096,
        )
        patched = raw.get("optimized_listing") or raw
        return _sanitize_optimized_listing({**listing, **patched})
    except Exception:
        return listing


def _build_rescore_payload(listing_data: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    bullets = optimized.get("bullets") or listing_data.get("bullets") or []
    if not isinstance(bullets, list):
        bullets = []
    base = _normalize_score_payload(listing_data)
    base.update({
        "title": str(optimized.get("title") or listing_data.get("title") or "").strip(),
        "bullets": [str(b).strip() for b in bullets if b and str(b).strip()],
        "description": str(optimized.get("description") or listing_data.get("description") or "").strip(),
        "search_terms": str(optimized.get("search_terms") or listing_data.get("search_terms") or "").strip(),
    })
    return base


def _sanitize_optimized_listing(ol: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(ol, dict):
        return {}
    if isinstance(ol.get("bullets"), list):
        ol["bullets"] = [_strip_emoji(str(b)) for b in ol["bullets"]]
    if isinstance(ol.get("title"), str):
        ol["title"] = _strip_emoji(ol["title"])[:200]
    if isinstance(ol.get("description"), str):
        ol["description"] = _strip_emoji(ol["description"])[:2000]
    if isinstance(ol.get("search_terms"), str):
        ol["search_terms"] = ol["search_terms"][:250]
    return ol


def _summarize_score_delta(before: int, after: int, before_result: dict, after_result: dict) -> str:
    if after <= before:
        return f"复评 {after}/100，未高于优化前 {before}/100"
    labels = {"title": "标题", "bullets": "Bullets", "description": "描述", "keywords": "关键词", "compliance": "合规"}
    improved = [f"{labels[k]}+{float((after_result.get('dimensions') or {}).get(k, {}).get('score', 0)) - float((before_result.get('dimensions') or {}).get(k, {}).get('score', 0)):.0f}"
                for k in labels if float((after_result.get("dimensions") or {}).get(k, {}).get("score", 0)) > float((before_result.get("dimensions") or {}).get(k, {}).get("score", 0))]
    detail = "、".join(improved) if improved else "各维度均有提升"
    partial = after_result.get("rescore_partial")
    extra = f"（部分复评：{','.join(after_result.get('rescore_dims_scored') or [])}）" if partial else ""
    return f"复评 verified：{before}→{after}（+{after - before}）{extra}，提升：{detail}"


def _strip_emoji(text: str) -> str:
    import re as _re
    return _re.sub(r'[\U0001F300-\U0001F9FF✀-➿☀-⛿︀-️✅❤✓✔✗✘☑]', '', text).strip()


def _format_dimensions_for_prompt(dims: dict) -> str:
    lines = []
    for key, dim in dims.items():
        score, max_s = dim.get("score", 0), dim.get("max", 20)
        header = f"{key}: {score}/{max_s}"
        if dim.get("weight_pct"):
            header += f" (权重{dim['weight_pct']}%)"
        if dim.get("rule_score") is not None:
            header += f" [规则{dim.get('rule_score')}+AI{dim.get('ai_score')}]"
        issues = dim.get("issues") or []
        issue_texts = [f"  - [{i.get('source', 'ai')}] {i.get('issue', '')}" + (f"\n    修复: {i['how_to_fix']}" if i.get("how_to_fix") else "") for i in issues if isinstance(i, dict)]
        lines.append(header + "\n" + ("\n".join(issue_texts) if issue_texts else "  (无问题)"))
    return "\n".join(lines)
