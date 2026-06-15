from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "store.db"

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _init_tables()
    return _conn


def _init_tables() -> None:
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS drafts (
            draft_no   TEXT PRIMARY KEY,
            data       TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_drafts_updated ON drafts(updated_at);

        CREATE TABLE IF NOT EXISTS tasks (
            task_no           TEXT PRIMARY KEY,
            status            TEXT NOT NULL DEFAULT 'READY',
            msku              TEXT NOT NULL DEFAULT '',
            store_id          INTEGER NOT NULL DEFAULT 0,
            record_unique_id  TEXT NOT NULL DEFAULT '',
            data              TEXT NOT NULL DEFAULT '{}',
            created_at        TEXT NOT NULL DEFAULT '',
            updated_at        TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
    """)
    conn.commit()
    _migrate_json_if_needed(conn)


def _migrate_json_if_needed(conn: sqlite3.Connection) -> None:
    drafts_file = DATA_DIR / "drafts.json"
    if drafts_file.exists():
        cur = conn.execute("SELECT COUNT(*) FROM drafts")
        if cur.fetchone()[0] == 0:
            try:
                raw = drafts_file.read_text("utf-8")
                items = json.loads(raw) if raw.strip() else []
                for item in items:
                    draft_no = str(item.get("draft_no", ""))
                    conn.execute(
                        "INSERT OR REPLACE INTO drafts (draft_no, data, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            draft_no,
                            json.dumps(item, ensure_ascii=False),
                            str(item.get("created_at", "")),
                            str(item.get("updated_at", "")),
                        ),
                    )
                conn.commit()
                _backup_file(drafts_file)
                print(f"[db] migrated {len(items)} drafts from JSON")
            except Exception as exc:
                print(f"[db] draft migration skipped: {exc}")

    tasks_file = DATA_DIR / "tasks.json"
    if tasks_file.exists():
        cur = conn.execute("SELECT COUNT(*) FROM tasks")
        if cur.fetchone()[0] == 0:
            try:
                raw = tasks_file.read_text("utf-8")
                items = json.loads(raw) if raw.strip() else []
                for item in items:
                    task_no = str(item.get("task_no", ""))
                    conn.execute(
                        "INSERT OR REPLACE INTO tasks "
                        "(task_no, status, msku, store_id, record_unique_id, "
                        " data, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
                _backup_file(tasks_file)
                print(f"[db] migrated {len(items)} tasks from JSON")
            except Exception as exc:
                print(f"[db] task migration skipped: {exc}")


def _backup_file(path: Path) -> None:
    """Rename path to .bak, with numbered fallback if .bak already exists."""
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        path.rename(bak)
        return
    for n in range(1, 100):
        bak = path.with_suffix(f"{path.suffix}.bak{n}")
        if not bak.exists():
            path.rename(bak)
            return


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def next_no(prefix: str, table: str, col: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    pattern = f"{prefix}-{today}%"
    conn = _get_conn()
    cur = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table} WHERE {col} LIKE ?", (pattern,))
    count = cur.fetchone()["cnt"]
    return f"{prefix}-{today}-{count + 1:04d}"


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return json.loads(row["data"])


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [json.loads(r["data"]) for r in rows]
