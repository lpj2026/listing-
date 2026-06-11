from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"

ACTIVE_POLL_STATUSES = {"SUBMITTED", "PROCESSING"}
ACTIVE_SYNC_STATUSES = {"LISTING_SYNCING"}
ACTIVE_TASK_STATUSES = ACTIVE_POLL_STATUSES | ACTIVE_SYNC_STATUSES
_lock = threading.Lock()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_tasks_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]", encoding="utf-8")


def load_tasks() -> list[dict[str, Any]]:
    ensure_tasks_file()
    raw = TASKS_FILE.read_text(encoding="utf-8")
    return json.loads(raw) if raw.strip() else []


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    ensure_tasks_file()
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def get_task(task_no: str) -> dict[str, Any] | None:
    with _lock:
        return next((item for item in load_tasks() if item.get("task_no") == task_no), None)


def update_task(task_no: str, updater: Callable[[dict[str, Any]], None]) -> dict[str, Any] | None:
    with _lock:
        tasks = load_tasks()
        task = next((item for item in tasks if item.get("task_no") == task_no), None)
        if task is None:
            return None
        updater(task)
        save_tasks(tasks)
        return task


def apply_poll_result(task: dict[str, Any], result: dict[str, Any]) -> bool:
    """Update task from poll result. Returns True when polling should stop."""
    task["publish_result"] = result.get("latest") or {}
    task["last_polled_at"] = now_text()
    task["poll_attempt"] = int(task.get("poll_attempt") or 0) + 1

    status = result.get("status")
    if status == 1:
        task["status"] = "LISTING_SYNCING"
        task["status_text"] = "刊登成功，等待 Listing 同步"
        task["publish_completed_at"] = now_text()
        return True
    if status == 2:
        task["status"] = "FAILED"
        task["status_text"] = "刊登失败"
        task["failure_reason"] = result.get("failure_reason") or ""
        task["completed_at"] = now_text()
        return True

    task["status"] = "PROCESSING"
    task["status_text"] = "刊登处理中"
    return False


def mark_poll_timeout(task: dict[str, Any]) -> None:
    task["status"] = "TIMEOUT"
    task["status_text"] = "轮询超时，请手动查结果"
    task["completed_at"] = now_text()


def mark_listing_sync_timeout(task: dict[str, Any]) -> None:
    task["status"] = "SYNC_TIMEOUT"
    task["status_text"] = "Listing 同步超时，请手动查询"
    task["completed_at"] = now_text()
