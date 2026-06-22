"""Listing score weights, grade thresholds, and weighted merge."""
from __future__ import annotations

from typing import Any

DIM_KEYS = ("title", "bullets", "description", "keywords", "compliance")

# 标题 + Bullets 权重更高（合计 100）
DIM_WEIGHTS: dict[str, int] = {
    "title": 25,
    "bullets": 25,
    "description": 20,
    "keywords": 15,
    "compliance": 15,
}

DEFAULT_GRADE_THRESHOLDS = {"excellent": 85, "good": 70, "fair": 55}


def get_grade_thresholds() -> dict[str, int]:
    """Calibrate from task history when scores are available; else defaults."""
    try:
        from task_store import load_tasks

        tasks = load_tasks() or []
        scored: list[tuple[int, bool]] = []
        for task in tasks:
            score = _task_listing_score(task)
            if score is None:
                continue
            failed = str(task.get("status") or "").upper() == "FAILED"
            scored.append((score, failed))
        if len(scored) >= 10:
            success_scores = [s for s, failed in scored if not failed]
            if len(success_scores) >= 5:
                success_scores.sort()
                p25 = success_scores[max(0, len(success_scores) // 4 - 1)]
                return {
                    "excellent": min(95, max(80, success_scores[-1] - 5)),
                    "good": max(55, p25),
                    "fair": max(45, p25 - 15),
                }
    except Exception:
        pass
    return dict(DEFAULT_GRADE_THRESHOLDS)


def _task_listing_score(task: dict[str, Any]) -> int | None:
    for key in ("listing_score", "overall_score", "score"):
        raw = task.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    data = task.get("data")
    if isinstance(data, dict):
        for key in ("listing_score", "overall_score", "score"):
            raw = data.get(key)
            if raw is not None:
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    pass
    return None


def grade_label(score: int, thresholds: dict[str, int] | None = None) -> str:
    t = thresholds or get_grade_thresholds()
    if score >= t["excellent"]:
        return "优秀"
    if score >= t["good"]:
        return "良好"
    if score >= t["fair"]:
        return "一般"
    return "需优化"


def scale_dimension(rule_pts: int, ai_pts: int, dim: str) -> dict[str, int | float]:
    """Scale rule (0-10) + AI (0-10) to weighted dimension max."""
    max_w = DIM_WEIGHTS.get(dim, 20)
    half = max_w / 2
    rule_scaled = round((max(0, min(10, rule_pts)) / 10) * half, 1)
    ai_scaled = round((max(0, min(10, ai_pts)) / 10) * half, 1)
    total = round(rule_scaled + ai_scaled, 1)
    return {
        "score": total,
        "max": max_w,
        "rule_score": rule_scaled,
        "ai_score": ai_scaled,
    }


def compute_weighted_total(dimensions: dict[str, Any]) -> int:
    total = sum(float((dimensions.get(k) or {}).get("score", 0)) for k in DIM_KEYS)
    return int(round(total))
