from __future__ import annotations

import os
import threading
import time
from typing import Any

from listing_service import find_listing_by_msku
from pair_service import pair_msku_to_local_sku
from task_store import load_tasks, mark_listing_sync_timeout, now_text, update_task


MAX_SYNC_SECONDS = int(os.environ.get("LISTING_SYNC_MAX_SECONDS", str(2 * 60 * 60)))
TICK_SECONDS = int(os.environ.get("LISTING_SYNC_TICK_SECONDS", "30"))
SYNC_POLL_DELAYS = [300, 300, 600, 600, 900]


def next_sync_delay(attempt: int) -> int:
    return SYNC_POLL_DELAYS[min(attempt, len(SYNC_POLL_DELAYS) - 1)]


def resolve_local_sku(task: dict[str, Any]) -> str:
    payload = task.get("payload") or {}
    raw_form = payload.get("raw_form") or {}
    return str(
        task.get("local_sku")
        or payload.get("local_sku")
        or raw_form.get("local_sku")
        or ""
    ).strip()


def resolve_seller_id(task: dict[str, Any]) -> str:
    payload = task.get("payload") or {}
    return str(task.get("seller_id") or payload.get("seller_id") or "").strip()


def try_pair_task(task: dict[str, Any]) -> tuple[bool, str]:
    local_sku = resolve_local_sku(task)
    if not local_sku:
        return False, "未填写本地 SKU，跳过自动配对"

    seller_id = resolve_seller_id(task)
    marketplace_id = str(task.get("marketplace_id") or "").strip()
    msku = str(task.get("msku") or "").strip()
    if not seller_id:
        return False, "缺少 seller_id，无法自动配对"

    try:
        pair_msku_to_local_sku(
            seller_id=seller_id,
            marketplace_id=marketplace_id,
            msku=msku,
            local_sku=local_sku,
        )
    except Exception as exc:
        return False, f"配对失败：{exc}"

    task["local_sku"] = local_sku
    task["status"] = "COMPLETED"
    task["status_text"] = "Listing 已同步，SKU 已配对"
    task["sku_paired"] = True
    task["completed_at"] = now_text()
    return True, "SKU 配对成功"


class ListingSyncWorker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._schedules: dict[str, dict[str, Any]] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._resume_pending()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="listing-sync")
        self._thread.start()
        print(f"[sync] worker started (max {MAX_SYNC_SECONDS}s)")

    def schedule(self, task_no: str) -> None:
        now = time.time()
        with self._lock:
            self._schedules[task_no] = {
                "next_at": now + next_sync_delay(0),
                "attempt": 0,
                "started_at": now,
            }
        print(f"[sync] scheduled {task_no}")

    def _resume_pending(self) -> None:
        for task in load_tasks():
            if task.get("status") == "LISTING_SYNCING":
                self.schedule(str(task["task_no"]))

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                print(f"[sync] worker error: {exc}")
            self._stop.wait(TICK_SECONDS)

    def _tick(self) -> None:
        now = time.time()
        with self._lock:
            due = [task_no for task_no, schedule in self._schedules.items() if schedule["next_at"] <= now]
        for task_no in due:
            self._sync_task(task_no, now)

    def _sync_task(self, task_no: str, now: float) -> None:
        with self._lock:
            schedule = self._schedules.get(task_no)
            if schedule is None:
                return

        task = next((item for item in load_tasks() if item.get("task_no") == task_no), None)
        if task is None or task.get("status") != "LISTING_SYNCING":
            self._remove(task_no)
            return

        if now - schedule["started_at"] >= MAX_SYNC_SECONDS:
            update_task(task_no, mark_listing_sync_timeout)
            print(f"[sync] timeout {task_no}")
            self._remove(task_no)
            return

        store_id = int(task.get("store_id") or 0)
        msku = str(task.get("msku") or "")
        try:
            listing = find_listing_by_msku(store_id, msku)
        except Exception as exc:
            print(f"[sync] listing query failed {task_no}: {exc}")
            self._defer(task_no, schedule, now)
            return

        if not listing:
            self._defer(task_no, schedule, now)
            return

        pair_message = ""

        def updater(item: dict[str, Any]) -> None:
            nonlocal pair_message
            item["listing_info"] = listing
            item["asin"] = listing.get("asin") or ""
            item["listing_synced_at"] = now_text()
            item["sync_attempt"] = int(item.get("sync_attempt") or 0) + 1
            paired, pair_message = try_pair_task(item)
            if not paired:
                item["status"] = "LISTING_SYNCED"
                item["status_text"] = pair_message

        update_task(task_no, updater)
        print(f"[sync] {task_no} -> listing found; {pair_message or 'done'}")
        self._remove(task_no)

    def _defer(self, task_no: str, schedule: dict[str, Any], now: float) -> None:
        attempt = int(schedule.get("attempt") or 0) + 1

        def updater(item: dict[str, Any]) -> None:
            item["sync_attempt"] = attempt
            item["status_text"] = f"等待 Listing 同步（已查 {attempt} 次）"

        update_task(task_no, updater)
        with self._lock:
            if task_no in self._schedules:
                self._schedules[task_no] = {
                    "next_at": now + next_sync_delay(attempt),
                    "attempt": attempt,
                    "started_at": schedule["started_at"],
                }

    def _remove(self, task_no: str) -> None:
        with self._lock:
            self._schedules.pop(task_no, None)


_worker = ListingSyncWorker()


def start_listing_sync_worker() -> None:
    _worker.start()


def schedule_listing_sync(task_no: str) -> None:
    _worker.schedule(task_no)


def check_listing_and_pair(task_no: str) -> dict[str, Any]:
    task = next((item for item in load_tasks() if item.get("task_no") == task_no), None)
    if task is None:
        raise ValueError("任务不存在")

    store_id = int(task.get("store_id") or 0)
    msku = str(task.get("msku") or "")
    listing = find_listing_by_msku(store_id, msku)
    if not listing:
        return {"found": False, "task": task}

    def updater(item: dict[str, Any]) -> None:
        item["listing_info"] = listing
        item["asin"] = listing.get("asin") or ""
        item["listing_synced_at"] = now_text()
        paired, message = try_pair_task(item)
        if not paired:
            item["status"] = "LISTING_SYNCED"
            item["status_text"] = message

    task = update_task(task_no, updater)
    return {"found": True, "task": task, "listing": listing}


def pair_task_now(task_no: str, local_sku: str = "") -> dict[str, Any]:
    task = next((item for item in load_tasks() if item.get("task_no") == task_no), None)
    if task is None:
        raise ValueError("任务不存在")

    def updater(item: dict[str, Any]) -> None:
        sku = (local_sku or item.get("local_sku") or "").strip()
        if sku:
            item["local_sku"] = sku
            payload = item.setdefault("payload", {})
            payload["local_sku"] = sku
            raw_form = payload.setdefault("raw_form", {})
            raw_form["local_sku"] = sku
        paired, message = try_pair_task(item)
        if not paired:
            raise ValueError(message)

    updated = update_task(task_no, updater)
    return {"task": updated}
