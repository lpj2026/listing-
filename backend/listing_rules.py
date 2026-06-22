"""Deterministic listing rule checks — aligned with Amazon / product form limits."""
from __future__ import annotations

import re
from typing import Any

# 与 frontend/index.html 及 Amazon 刊登约束对齐
TITLE_MAX = 200
TITLE_IDEAL_MIN = 150
BULLET_MAX = 500
BULLET_IDEAL_MIN = 80
BULLET_IDEAL_MAX = 250
BULLET_COUNT = 5
DESC_MAX = 2000
DESC_QUALITY_MIN = 500
SEARCH_TERMS_MAX = 250
IMAGE_MAX = 9
IMAGE_RECOMMENDED = 7
BULLET_SIMILARITY_THRESHOLD = 0.6

PROHIBITED_WORDS = (
    "best seller",
    "best selling",
    "#1",
    "number 1",
    "guaranteed",
    "risk free",
    "risk-free",
    "fda approved",
    "miracle",
    "cure",
    "100% safe",
    "free shipping",
    "lowest price",
    "cheapest",
)

from listing_score_model import (
    DIM_KEYS,
    DIM_WEIGHTS,
    compute_weighted_total,
    get_grade_thresholds,
    grade_label,
    scale_dimension,
)

RULES_PER_DIM = 10

_EMOJI_RE = re.compile(r"[\U0001F300-\U0001F9FF✀-➿☀-⛿︀-️✅❤✓✔✗✘☑]")
_HTML_RE = re.compile(r"</?(p|ul|ol|li|b|strong|br|div|span|h[1-6])\b", re.I)
_ST_PUNCT_RE = re.compile(r"[,;.'\"!?@#$%^&*+=|/\\<>()\[\]{}]")


def _norm_listing(data: dict[str, Any]) -> dict[str, Any]:
    title = str(data.get("title", "")).strip()
    bullets_raw = data.get("bullets") or []
    if isinstance(bullets_raw, list):
        bullets = [str(b).strip() for b in bullets_raw if b and str(b).strip()]
    else:
        bullets = []

    raw_img = data.get("image_count")
    image_count: int | None
    if raw_img is None or raw_img == "":
        image_count = None
    else:
        try:
            image_count = int(raw_img)
        except (TypeError, ValueError):
            image_count = None

    images_linked = bool(data.get("images_linked"))

    return {
        "title": title,
        "bullets": bullets,
        "description": str(data.get("description", "")).strip(),
        "search_terms": str(data.get("search_terms", "")).strip(),
        "image_count": image_count,
        "images_linked": images_linked,
        "brand": str(data.get("brand", "")).strip(),
    }


def _content_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-z0-9]+", text) if len(w) >= 3}


def _has_prohibited_in_fields(
    fields: dict[str, str],
) -> tuple[list[str], dict[str, list[str]]]:
    """Return unique prohibited phrases and which fields contain each."""
    found: set[str] = set()
    by_field: dict[str, list[str]] = {}
    for field_name, text in fields.items():
        if not text:
            continue
        lower = text.lower()
        hits: list[str] = []
        for phrase in PROHIBITED_WORDS:
            if " " in phrase:
                if phrase in lower:
                    hits.append(phrase)
            elif re.search(rf"\b{re.escape(phrase)}\b", lower):
                hits.append(phrase)
        if hits:
            by_field[field_name] = hits
            found.update(hits)
    return sorted(found), by_field


def _has_emoji(text: str) -> bool:
    return bool(_EMOJI_RE.search(text))


def _emoji_fields(fields: dict[str, str]) -> list[str]:
    return [name for name, text in fields.items() if text and _has_emoji(text)]


def _bullet_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _search_terms_tokens(text: str) -> list[str]:
    return [w.lower() for w in re.split(r"\s+", text.strip()) if len(w) >= 2]


def _title_all_caps_abuse(title: str) -> bool:
    letters = [c for c in title if c.isalpha()]
    if len(letters) < 10:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) > 0.7


def _title_exclamation_abuse(title: str) -> bool:
    return title.count("!") > 1 or "!!" in title


def _bullet_near_duplicate_indices(bullets: list[str]) -> list[int]:
    """Detect bullets with high keyword overlap (near-duplicate selling points)."""
    word_sets = [_content_words(b) for b in bullets]
    dup_indices: set[int] = set()

    for i in range(len(bullets)):
        for j in range(i + 1, len(bullets)):
            a, b = word_sets[i], word_sets[j]
            if not a or not b:
                continue
            overlap_ratio = len(a & b) / min(len(a), len(b))
            if overlap_ratio >= BULLET_SIMILARITY_THRESHOLD:
                dup_indices.add(i + 1)
                dup_indices.add(j + 1)

    keys = [_bullet_key(b) for b in bullets]
    for i, k in enumerate(keys):
        if k and keys.count(k) > 1:
            dup_indices.add(i + 1)

    return sorted(dup_indices)


def _search_terms_punctuation_issues(text: str) -> list[str]:
    issues: list[str] = []
    if _ST_PUNCT_RE.search(text):
        found = sorted(set(_ST_PUNCT_RE.findall(text)))
        issues.append(f"含标点: {''.join(found[:6])}")
    if re.search(r"\s{2,}", text):
        issues.append("含连续空格")
    if text != text.lower() and re.search(r"[A-Z]", text):
        issues.append("含大写字母（后台搜索词建议全小写）")
    return issues


def _field_label(name: str) -> str:
    return {
        "title": "标题",
        "bullets": "Bullets",
        "description": "描述",
        "search_terms": "Search Terms",
    }.get(name, name)


def _issue(message: str, how_to_fix: str, *, rule_id: str) -> dict[str, str]:
    return {
        "issue": message,
        "why_matters": "不符合 Amazon 刊登硬性/推荐约束，可能影响审核或转化",
        "how_to_fix": how_to_fix,
        "expected_gain": "修复后可恢复该规则项得分",
        "rule_id": rule_id,
        "source": "rule",
    }


def compute_rule_score(data: dict[str, Any]) -> dict[str, Any]:
    """Return per-dimension rule scores (0-10 each) and check details."""
    listing = _norm_listing(data)
    title = listing["title"]
    bullets = listing["bullets"]
    description = listing["description"]
    search_terms = listing["search_terms"]
    image_count = listing["image_count"]
    images_linked = listing["images_linked"]
    brand = listing["brand"]

    text_fields = {
        "title": title,
        "bullets": " ".join(bullets),
        "description": description,
        "search_terms": search_terms,
    }

    dim_scores: dict[str, dict[str, Any]] = {
        key: {"score": 0, "max": RULES_PER_DIM, "issues": [], "positives": []}
        for key in DIM_KEYS
    }
    checks: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}

    def add_check(
        *,
        dim: str,
        rule_id: str,
        passed: bool,
        points: int,
        message: str,
        fix: str = "",
        positive: str = "",
        skipped: bool = False,
    ) -> None:
        checks.append({
            "id": rule_id,
            "dimension": dim,
            "passed": passed,
            "points": points if passed else 0,
            "max_points": points,
            "message": message,
            "skipped": skipped,
        })
        if passed:
            dim_scores[dim]["score"] += points
            if positive:
                dim_scores[dim]["positives"].append(positive)
        elif fix and not skipped:
            dim_scores[dim]["issues"].append(_issue(message, fix, rule_id=rule_id))

    # ── Title (10) ──────────────────────────────────────────────
    tlen = len(title)

    if tlen <= TITLE_MAX:
        add_check(
            dim="title", rule_id="title_amazon_limit", passed=True, points=2,
            message=f"标题 {tlen} 字符，未超过 Amazon 上限 {TITLE_MAX}",
            positive="标题长度符合平台上限",
        )
    else:
        add_check(
            dim="title", rule_id="title_amazon_limit", passed=False, points=2,
            message=f"标题 {tlen} 字符，超过 Amazon 上限 {TITLE_MAX}",
            fix=f"精简至 {TITLE_MAX} 字符以内（与刊登表单 item_name 一致）",
        )

    if TITLE_IDEAL_MIN <= tlen <= TITLE_MAX:
        add_check(
            dim="title", rule_id="title_length_ideal", passed=True, points=3,
            message=f"标题 {tlen} 字符，在推荐区间 {TITLE_IDEAL_MIN}-{TITLE_MAX}",
            positive="标题长度利于搜索展示",
        )
    elif 0 < tlen < TITLE_IDEAL_MIN:
        add_check(
            dim="title", rule_id="title_length_ideal", passed=False, points=3,
            message=f"标题仅 {tlen} 字符，低于推荐下限 {TITLE_IDEAL_MIN}",
            fix=f"扩展至 {TITLE_IDEAL_MIN}-{TITLE_MAX} 字符，补充核心词、品牌与规格",
        )
    elif tlen == 0:
        add_check(
            dim="title", rule_id="title_length_ideal", passed=False, points=3,
            message="标题为空", fix="填写完整英文标题",
        )

    if title and re.search(r"[A-Za-z]", title):
        add_check(
            dim="title", rule_id="title_has_text", passed=True, points=1,
            message="标题含有效英文", positive="标题可读",
        )
    else:
        add_check(
            dim="title", rule_id="title_has_text", passed=False, points=1,
            message="标题缺少有效英文内容", fix="填写英文标题",
        )

    if brand:
        if brand.lower() in title.lower():
            add_check(
                dim="title", rule_id="title_brand", passed=True, points=2,
                message=f"标题包含品牌「{brand}」", positive="品牌已展示",
            )
        else:
            add_check(
                dim="title", rule_id="title_brand", passed=False, points=2,
                message=f"标题未包含品牌「{brand}」",
                fix="在标题前部加入品牌名（Amazon 推荐做法）",
            )
    else:
        add_check(
            dim="title", rule_id="title_brand", passed=False, points=2,
            message="未填写品牌，无法校验标题是否含品牌",
            fix="在「补充信息」填写品牌，或在标题前部加入品牌名",
        )

    title_fmt_issues: list[str] = []
    if title and _title_all_caps_abuse(title):
        title_fmt_issues.append("大段全大写")
    if title and _title_exclamation_abuse(title):
        title_fmt_issues.append("滥用感叹号")
    if title and not title_fmt_issues:
        add_check(
            dim="title", rule_id="title_format", passed=True, points=2,
            message="标题格式规范（无全大写滥用、感叹号适中）",
            positive="标题格式专业",
        )
    elif title:
        add_check(
            dim="title", rule_id="title_format", passed=False, points=2,
            message=f"标题格式问题: {'、'.join(title_fmt_issues)}",
            fix="使用 Title Case 或句首大写，避免全大写单词堆叠；感叹号最多 1 个",
        )
    else:
        add_check(
            dim="title", rule_id="title_format", passed=False, points=2,
            message="标题为空", fix="填写标题",
        )

    # ── Bullets (10) ────────────────────────────────────────────
    bcount = len(bullets)
    if bcount == BULLET_COUNT:
        add_check(
            dim="bullets", rule_id="bullet_count", passed=True, points=4,
            message=f"{BULLET_COUNT} 条 Bullet Points", positive="Bullet 数量完整",
        )
    else:
        add_check(
            dim="bullets", rule_id="bullet_count", passed=False, points=4,
            message=f"当前 {bcount} 条 Bullet，Amazon 建议 {BULLET_COUNT} 条",
            fix=f"补齐至 {BULLET_COUNT} 条，每条覆盖不同卖点",
        )

    over_hard = [i + 1 for i, b in enumerate(bullets) if len(b) > BULLET_MAX]
    under_min = [i + 1 for i, b in enumerate(bullets) if len(b) < BULLET_IDEAL_MIN]
    over_ideal = [i + 1 for i, b in enumerate(bullets) if BULLET_IDEAL_MAX < len(b) <= BULLET_MAX]

    if not bullets:
        add_check(
            dim="bullets", rule_id="bullet_length", passed=False, points=3,
            message="缺少 Bullet Points",
            fix=f"添加 {BULLET_COUNT} 条卖点，每条 {BULLET_IDEAL_MIN}-{BULLET_IDEAL_MAX} 字符",
        )
    elif over_hard:
        add_check(
            dim="bullets", rule_id="bullet_length", passed=False, points=3,
            message=f"第 {', '.join(map(str, over_hard))} 条超过 Amazon 上限 {BULLET_MAX} 字符",
            fix=f"每条 Bullet 不超过 {BULLET_MAX} 字符（与刊登表单一致）",
        )
    elif under_min:
        add_check(
            dim="bullets", rule_id="bullet_length", passed=False, points=3,
            message=f"第 {', '.join(map(str, under_min))} 条不足 {BULLET_IDEAL_MIN} 字符",
            fix=f"每条扩展至 {BULLET_IDEAL_MIN}-{BULLET_IDEAL_MAX} 字符",
        )
    elif over_ideal:
        add_check(
            dim="bullets", rule_id="bullet_length", passed=False, points=3,
            message=f"第 {', '.join(map(str, over_ideal))} 条偏长（>{BULLET_IDEAL_MAX}）",
            fix=f"精简至 {BULLET_IDEAL_MAX} 字符以内，保留核心利益点",
        )
    else:
        add_check(
            dim="bullets", rule_id="bullet_length", passed=True, points=3,
            message=f"各条长度 {BULLET_IDEAL_MIN}-{BULLET_IDEAL_MAX} 字符",
            positive="Bullet 长度合规",
        )

    near_dupes = _bullet_near_duplicate_indices(bullets)
    if bullets and not near_dupes:
        add_check(
            dim="bullets", rule_id="bullet_unique", passed=True, points=3,
            message="各条 Bullet 卖点互不重复", positive="卖点覆盖完整",
        )
    elif near_dupes:
        add_check(
            dim="bullets", rule_id="bullet_unique", passed=False, points=3,
            message=f"第 {', '.join(map(str, near_dupes))} 条卖点重复或高度相似",
            fix="每条 Bullet 应覆盖不同功能/场景/规格，避免同义反复",
        )
    else:
        add_check(
            dim="bullets", rule_id="bullet_unique", passed=False, points=3,
            message="无法检测 Bullet 唯一性", fix="填写 Bullet Points",
        )

    # ── Description (10) ──────────────────────────────────────
    dlen = len(description)

    if not description:
        add_check(
            dim="description", rule_id="desc_present", passed=False, points=3,
            message="未填写产品描述", fix="补充产品描述",
        )
        add_check(
            dim="description", rule_id="desc_amazon_limit", passed=False, points=2,
            message="描述为空", fix=f"填写描述，上限 {DESC_MAX} 字符",
        )
        add_check(
            dim="description", rule_id="desc_quality", passed=False, points=5,
            message="描述为空", fix=f"扩展至 {DESC_QUALITY_MIN}+ 字符并使用 HTML 格式",
        )
    else:
        add_check(
            dim="description", rule_id="desc_present", passed=True, points=3,
            message="已填写产品描述", positive="描述已提供",
        )
        if dlen <= DESC_MAX:
            add_check(
                dim="description", rule_id="desc_amazon_limit", passed=True, points=2,
                message=f"描述 {dlen} 字符，未超过上限 {DESC_MAX}",
                positive="描述长度符合表单限制",
            )
        else:
            add_check(
                dim="description", rule_id="desc_amazon_limit", passed=False, points=2,
                message=f"描述 {dlen} 字符，超过上限 {DESC_MAX}",
                fix=f"精简至 {DESC_MAX} 字符以内（与刊登表单 product_description 一致）",
            )

        has_html = bool(_HTML_RE.search(description))
        if dlen >= DESC_QUALITY_MIN and has_html:
            add_check(
                dim="description", rule_id="desc_quality", passed=True, points=5,
                message=f"描述 {dlen} 字符且含 HTML 结构", positive="描述完整规范",
            )
        else:
            parts = []
            if dlen < DESC_QUALITY_MIN:
                parts.append(f"仅 {dlen} 字符，建议 ≥{DESC_QUALITY_MIN}")
            if not has_html:
                parts.append("缺少 HTML 标签")
            add_check(
                dim="description", rule_id="desc_quality", passed=False, points=5,
                message="；".join(parts) or "描述质量不足",
                fix="使用 <b>、<ul>、<li>、<p> 等 HTML，扩展至 500+ 字符",
            )

    # ── Keywords (10) ─────────────────────────────────────────
    st_len = len(search_terms)
    if 0 < st_len <= SEARCH_TERMS_MAX:
        add_check(
            dim="keywords", rule_id="search_terms_length", passed=True, points=4,
            message=f"Search Terms {st_len}/{SEARCH_TERMS_MAX} 字符",
            positive="Search Terms 长度合规",
        )
    elif st_len == 0:
        add_check(
            dim="keywords", rule_id="search_terms_length", passed=False, points=4,
            message="未填写 Search Terms",
            fix=f"补充 {SEARCH_TERMS_MAX} 字符以内的后台搜索词",
        )
    else:
        add_check(
            dim="keywords", rule_id="search_terms_length", passed=False, points=4,
            message=f"Search Terms {st_len} 字符，超过上限 {SEARCH_TERMS_MAX}",
            fix=f"精简至 {SEARCH_TERMS_MAX} 字符（与 generic_keyword 字段一致）",
        )

    title_ws = _content_words(title)
    bullet_ws: set[str] = set()
    for b in bullets:
        bullet_ws |= _content_words(b)
    st_ws = _content_words(search_terms)
    overlap_title = title_ws & st_ws
    overlap_bullets = bullet_ws & st_ws

    if search_terms and not overlap_title and not overlap_bullets:
        add_check(
            dim="keywords", rule_id="search_terms_distinct", passed=True, points=3,
            message="Search Terms 与标题、Bullets 关键词区分良好",
            positive="关键词互补",
        )
    elif not search_terms:
        add_check(
            dim="keywords", rule_id="search_terms_distinct", passed=False, points=3,
            message="无法评估关键词区分度", fix="填写 Search Terms",
        )
    else:
        parts = []
        if overlap_title:
            parts.append(f"与标题重复: {', '.join(sorted(overlap_title)[:6])}")
        if overlap_bullets:
            parts.append(f"与 Bullets 重复: {', '.join(sorted(overlap_bullets)[:6])}")
        add_check(
            dim="keywords", rule_id="search_terms_distinct", passed=False, points=3,
            message="；".join(parts),
            fix="Search Terms 使用标题与 Bullets 未覆盖的同义词、变体与长尾词",
        )

    st_tokens = _search_terms_tokens(search_terms)
    st_dupes = {t for t in st_tokens if st_tokens.count(t) > 1}
    if search_terms and not st_dupes:
        add_check(
            dim="keywords", rule_id="search_terms_no_dup", passed=True, points=2,
            message="Search Terms 无重复词", positive="关键词利用率高",
        )
    elif st_dupes:
        add_check(
            dim="keywords", rule_id="search_terms_no_dup", passed=False, points=2,
            message=f"Search Terms 重复: {', '.join(sorted(st_dupes)[:6])}",
            fix="删除重复词，用单个空格分隔不同关键词",
        )
    elif not search_terms:
        add_check(
            dim="keywords", rule_id="search_terms_no_dup", passed=False, points=2,
            message="Search Terms 为空", fix="填写 Search Terms",
        )

    st_fmt = _search_terms_punctuation_issues(search_terms)
    if search_terms and not st_fmt:
        add_check(
            dim="keywords", rule_id="search_terms_format", passed=True, points=1,
            message="Search Terms 格式规范（小写、空格分隔、无标点）",
            positive="后台搜索词格式合规",
        )
    elif search_terms:
        add_check(
            dim="keywords", rule_id="search_terms_format", passed=False, points=1,
            message=f"Search Terms 格式问题: {'；'.join(st_fmt)}",
            fix="全小写、仅用空格分隔，勿用逗号/分号/引号等标点",
        )
    elif not search_terms:
        add_check(
            dim="keywords", rule_id="search_terms_format", passed=False, points=1,
            message="Search Terms 为空", fix="填写 Search Terms",
        )

    # ── Compliance (10) ───────────────────────────────────────
    image_known = images_linked or (image_count is not None and image_count > 0)
    if not image_known:
        add_check(
            dim="compliance", rule_id="image_count", passed=True, points=4,
            message="未关联产品图，图片项跳过（合规分仅供参考）",
            positive="请从产品页导入或手动填写图片数量",
            skipped=True,
        )
        meta["image_score_skipped"] = True
    elif image_count is not None and image_count >= IMAGE_RECOMMENDED:
        add_check(
            dim="compliance", rule_id="image_count", passed=True, points=4,
            message=f"{image_count} 张图片（建议 {IMAGE_RECOMMENDED}+，上限 {IMAGE_MAX}）",
            positive="主图数量充足",
        )
    elif image_count is not None and image_count >= 1:
        add_check(
            dim="compliance", rule_id="image_count", passed=False, points=4,
            message=f"仅 {image_count} 张图片，建议 {IMAGE_RECOMMENDED}+ 张",
            fix="补充场景图、细节图、尺寸图等",
        )
    else:
        add_check(
            dim="compliance", rule_id="image_count", passed=False, points=4,
            message="未提供图片（刊登至少需 1 张主图）",
            fix="至少上传 1 张主图，建议 7 张",
        )

    all_bad, bad_by_field = _has_prohibited_in_fields(text_fields)
    if not all_bad:
        add_check(
            dim="compliance", rule_id="prohibited_words", passed=True, points=4,
            message="全文无已知违禁表达", positive="文案合规",
        )
    else:
        loc_parts = [
            f"{_field_label(field)}({', '.join(sorted(set(hits))[:3])})"
            for field, hits in bad_by_field.items()
        ]
        add_check(
            dim="compliance", rule_id="prohibited_words", passed=False, points=4,
            message=f"违禁表达: {', '.join(all_bad[:5])} · 出现于 {'、'.join(loc_parts)}",
            fix="删除 best、#1、guaranteed 等绝对化或违规用语（合规维度仅计一次）",
        )

    emoji_locs = _emoji_fields(text_fields)
    if not emoji_locs:
        add_check(
            dim="compliance", rule_id="emoji_free", passed=True, points=2,
            message="全文无 emoji/装饰符号", positive="格式符合 Amazon 规范",
        )
    else:
        add_check(
            dim="compliance", rule_id="emoji_free", passed=False, points=2,
            message=f"{'、'.join(_field_label(f) for f in emoji_locs)} 含 emoji 或装饰符号",
            fix="Listing 文案中避免使用 emoji 与装饰性符号",
        )

    rule_score = sum(dim_scores[k]["score"] for k in DIM_KEYS)
    passed_count = sum(1 for c in checks if c["passed"])
    return {
        "rule_score": rule_score,
        "rule_max": len(DIM_KEYS) * RULES_PER_DIM,
        "checks_passed": passed_count,
        "checks_total": len(checks),
        "checks": checks,
        "dimensions": dim_scores,
        "meta": meta,
    }


def format_rules_for_prompt(rule_result: dict[str, Any]) -> str:
    lines = [
        f"Rule score: {rule_result.get('rule_score', 0)}/{rule_result.get('rule_max', 50)} "
        f"({rule_result.get('checks_passed', 0)}/{rule_result.get('checks_total', 0)} checks passed)",
        "Amazon-aligned hard limits already evaluated. Focus AI scoring on copy quality only.",
        "Do NOT re-flag: brand in title, bullet count/uniqueness, emoji, prohibited words, "
        "search term format/overlap, title caps/exclamation, or image count.",
    ]
    for check in rule_result.get("checks") or []:
        status = "PASS" if check.get("passed") else "FAIL"
        skip = " (skipped)" if check.get("skipped") else ""
        lines.append(f"- [{status}] {check.get('id')}: {check.get('message')}{skip}")
    return "\n".join(lines)


_AI_DEDUP_PATTERNS = re.compile(
    r"违禁|prohibited|emoji|品牌.*标题|title.*brand|字符|长度|上限|"
    r"search.?term|重复词|标点|大写|感叹|bullet.*重复|图片",
    re.I,
)


def _filter_ai_issues(ai_issues: list[Any], rule_issues: list[Any]) -> list[Any]:
    """Drop AI issues that duplicate deterministic rule findings."""
    if not ai_issues:
        return []
    rule_text = " ".join(
        str(i.get("issue", "")) + str(i.get("how_to_fix", ""))
        for i in rule_issues
        if isinstance(i, dict)
    ).lower()
    filtered: list[Any] = []
    for issue in ai_issues:
        if not isinstance(issue, dict):
            continue
        text = f"{issue.get('issue', '')} {issue.get('how_to_fix', '')}".lower()
        if _AI_DEDUP_PATTERNS.search(text) and (
            _AI_DEDUP_PATTERNS.search(rule_text) or len(rule_issues) > 0
        ):
            continue
        filtered.append(issue)
    return filtered


def merge_rule_and_ai_scores(rule_result: dict[str, Any], ai_result: dict[str, Any]) -> dict[str, Any]:
    """Combine rule + AI with weighted dimensions (title/bullets 25% each)."""
    ai_dims = ai_result.get("dimensions") or {}
    merged_dims: dict[str, Any] = {}
    thresholds = get_grade_thresholds()

    rule_total = 0.0
    ai_total = 0.0

    for key in DIM_KEYS:
        rule_dim = (rule_result.get("dimensions") or {}).get(key, {})
        ai_dim = ai_dims.get(key, {})
        rule_pts = int(rule_dim.get("score", 0))
        ai_raw = int(ai_dim.get("score", 0))
        ai_max = int(ai_dim.get("max", 10)) or 10
        ai_pts = max(0, min(10, round(ai_raw * 10 / ai_max))) if ai_max else 0

        scaled = scale_dimension(rule_pts, ai_pts, key)
        rule_total += float(scaled["rule_score"])
        ai_total += float(scaled["ai_score"])

        rule_issues = list(rule_dim.get("issues") or [])
        ai_issues = _filter_ai_issues(ai_dim.get("issues") or [], rule_issues)

        merged_issues = list(rule_issues)
        for issue in ai_issues:
            if isinstance(issue, dict):
                item = dict(issue)
                item.setdefault("source", "ai")
                merged_issues.append(item)

        merged_dims[key] = {
            **scaled,
            "weight_pct": DIM_WEIGHTS.get(key, 20),
            "positives": list(rule_dim.get("positives") or []) + list(ai_dim.get("positives") or []),
            "issues": merged_issues,
        }

    overall = compute_weighted_total(merged_dims)
    result = {
        "overall_score": overall,
        "overall_grade": grade_label(overall, thresholds),
        "grade_thresholds": thresholds,
        "overall_summary": ai_result.get("overall_summary", ""),
        "top_priority": ai_result.get("top_priority") or [],
        "dimensions": merged_dims,
        "rule_score": int(round(rule_total)),
        "ai_score": int(round(ai_total)),
        "rule_checks": rule_result.get("checks") or [],
        "score_model": "weighted_v1",
    }
    meta = rule_result.get("meta") or {}
    if meta.get("image_score_skipped"):
        result["image_score_skipped"] = True
        note = "未关联产品图，图片合规项已跳过，总分中合规维度仅供参考"
        result["overall_summary"] = (
            f"{result['overall_summary']} {note}".strip()
            if result.get("overall_summary")
            else note
        )
    return result


def _grade(score: int) -> str:
    return grade_label(score)
