from __future__ import annotations

import json
from typing import Any, Callable

from record_store import _get_conn, _lock, _row_to_dict, _rows_to_list, next_no, now_text

ACTIVE_POLL_STATUSES = {"SUBMITTED", "PROCESSING"}
ACTIVE_SYNC_STATUSES = {"LISTING_SYNCING"}
ACTIVE_TASK_STATUSES = ACTIVE_POLL_STATUSES | ACTIVE_SYNC_STATUSES


def load_tasks() -> list[dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute("SELECT data FROM tasks ORDER BY created_at DESC").fetchall()
    return _rows_to_list(rows)


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    """Bulk replace all tasks. Only used externally if at all; prefer create_task / update_task."""
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM tasks")
        for item in tasks:
            task_no = str(item.get("task_no", ""))
            conn.execute(
                "INSERT INTO tasks (task_no, status, msku, store_id, record_unique_id, "
                "data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_no,
                    str(item.get("status", "READY")),
                    str(item.get("msku", "")),
                    int(item.get("store_id") or 0),
                    str(item.get("record_unique_id", "")),
                    json.dumps(item, ensure_ascii=False),
                    str(item.get("created_at", "")),
                    str(item.get("updated_at", "")),
                ),
            )
        conn.commit()


def get_task(task_no: str) -> dict[str, Any] | None:
    conn = _get_conn()
    row = conn.execute("SELECT data FROM tasks WHERE task_no = ?", (task_no,)).fetchone()
    return _row_to_dict(row)


def create_task(task: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        conn = _get_conn()
        if not task.get("task_no"):
            task["task_no"] = next_no("TASK", "tasks", "task_no")
        task.setdefault("created_at", now_text())
        task.setdefault("updated_at", "")
        task.setdefault("status", "READY")
        task.setdefault("msku", "")
        task.setdefault("store_id", 0)
        task.setdefault("record_unique_id", "")

        conn.execute(
            "INSERT INTO tasks (task_no, status, msku, store_id, record_unique_id, "
            "data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task["task_no"],
                task["status"],
                task["msku"],
                int(task.get("store_id") or 0),
                task["record_unique_id"],
                json.dumps(task, ensure_ascii=False),
                task["created_at"],
                task["updated_at"],
            ),
        )
        conn.commit()
        return task


def update_task(
    task_no: str, updater: Callable[[dict[str, Any]], None]
) -> dict[str, Any] | None:
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT data FROM tasks WHERE task_no = ?", (task_no,)).fetchone()
        if row is None:
            return None
        task = json.loads(row["data"])
        updater(task)
        task["updated_at"] = now_text()
        conn.execute(
            "UPDATE tasks SET data = ?, status = ?, msku = ?, store_id = ?, "
            "record_unique_id = ?, updated_at = ? WHERE task_no = ?",
            (
                json.dumps(task, ensure_ascii=False),
                str(task.get("status", "READY")),
                str(task.get("msku", "")),
                int(task.get("store_id") or 0),
                str(task.get("record_unique_id", "")),
                task["updated_at"],
                task_no,
            ),
        )
        conn.commit()
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
