from __future__ import annotations

import os
import threading
import time
from typing import Any

from publish_service import query_publish_result
from sync_worker import schedule_listing_sync
from task_store import ACTIVE_POLL_STATUSES, apply_poll_result, load_tasks, mark_poll_timeout, update_task


MAX_POLL_SECONDS = int(os.environ.get("PUBLISH_POLL_MAX_SECONDS", str(15 * 60)))
TICK_SECONDS = int(os.environ.get("PUBLISH_POLL_TICK_SECONDS", "5"))


def next_poll_delay(attempt: int) -> int:
    delays = [30, 30, 60, 120]
    return delays[min(attempt, len(delays) - 1)]


class PublishPollWorker:
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
        self._thread = threading.Thread(target=self._loop, daemon=True, name="publish-poll")
        self._thread.start()
        print(f"[poll] worker started (max {MAX_POLL_SECONDS}s)")

    def schedule(self, task_no: str) -> None:
        now = time.time()
        with self._lock:
            self._schedules[task_no] = {
                "next_at": now + next_poll_delay(0),
                "attempt": 0,
                "started_at": now,
            }
        print(f"[poll] scheduled {task_no}")

    def _resume_pending(self) -> None:
        for task in load_tasks():
            if task.get("status") in ACTIVE_POLL_STATUSES and task.get("record_unique_id"):
                self.schedule(str(task["task_no"]))

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                print(f"[poll] worker error: {exc}")
            self._stop.wait(TICK_SECONDS)

    def _tick(self) -> None:
        now = time.time()
        with self._lock:
            due = [task_no for task_no, schedule in self._schedules.items() if schedule["next_at"] <= now]

        for task_no in due:
            self._poll_task(task_no, now)

    def _poll_task(self, task_no: str, now: float) -> None:
        with self._lock:
            schedule = self._schedules.get(task_no)
            if schedule is None:
                return

        task = next((item for item in load_tasks() if item.get("task_no") == task_no), None)
        if task is None:
            self._remove(task_no)
            return

        if task.get("status") not in ACTIVE_POLL_STATUSES:
            self._remove(task_no)
            return

        record_unique_id = str(task.get("record_unique_id") or "")
        if not record_unique_id:
            self._remove(task_no)
            return

        if now - schedule["started_at"] >= MAX_POLL_SECONDS:
            update_task(task_no, mark_poll_timeout)
            print(f"[poll] timeout {task_no}")
            self._remove(task_no)
            return

        try:
            result = query_publish_result(
                record_unique_id=record_unique_id,
                store_id=int(task.get("store_id") or 0) or None,
                sku=str(task.get("msku") or ""),
            )
        except Exception as exc:
            print(f"[poll] query failed {task_no}: {exc}")
            self._defer(task_no, schedule, now)
            return

        finished = False

        def updater(item: dict[str, Any]) -> None:
            nonlocal finished
            finished = apply_poll_result(item, result)

        update_task(task_no, updater)
        status_text = result.get("status_text") or "UNKNOWN"
        print(f"[poll] {task_no} -> {status_text}")

        if finished:
            task = next((item for item in load_tasks() if item.get("task_no") == task_no), None)
            if task and task.get("status") == "LISTING_SYNCING":
                schedule_listing_sync(task_no)
            self._remove(task_no)
            return

        self._defer(task_no, schedule, now)

    def _defer(self, task_no: str, schedule: dict[str, Any], now: float) -> None:
        attempt = int(schedule.get("attempt") or 0) + 1
        with self._lock:
            if task_no in self._schedules:
                self._schedules[task_no] = {
                    "next_at": now + next_poll_delay(attempt),
                    "attempt": attempt,
                    "started_at": schedule["started_at"],
                }

    def _remove(self, task_no: str) -> None:
        with self._lock:
            self._schedules.pop(task_no, None)


_worker = PublishPollWorker()


def start_publish_worker() -> None:
    _worker.start()


def schedule_publish_poll(task_no: str) -> None:
    _worker.schedule(task_no)
