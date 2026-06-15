from __future__ import annotations

import json
from typing import Any

from record_store import _get_conn, _lock, _row_to_dict, _rows_to_list, next_no, now_text


def list_drafts() -> list[dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute("SELECT data FROM drafts ORDER BY updated_at DESC").fetchall()
    return _rows_to_list(rows)


def get_draft(draft_no: str) -> dict[str, Any] | None:
    conn = _get_conn()
    row = conn.execute("SELECT data FROM drafts WHERE draft_no = ?", (draft_no,)).fetchone()
    return _row_to_dict(row)


def save_draft(payload: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        conn = _get_conn()
        draft_no = payload.get("draft_no")

        if draft_no:
            existing = conn.execute(
                "SELECT data FROM drafts WHERE draft_no = ?", (draft_no,)
            ).fetchone()
        else:
            existing = None

        if existing:
            saved = json.loads(existing["data"])
            saved.update(payload)
            saved["updated_at"] = now_text()
            conn.execute(
                "UPDATE drafts SET data = ?, updated_at = ? WHERE draft_no = ?",
                (json.dumps(saved, ensure_ascii=False), saved["updated_at"], draft_no),
            )
        else:
            saved = {**payload}
            saved["draft_no"] = next_no("DRAFT", "drafts", "draft_no")
            saved["created_at"] = now_text()
            saved["updated_at"] = now_text()
            conn.execute(
                "INSERT INTO drafts (draft_no, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (
                    saved["draft_no"],
                    json.dumps(saved, ensure_ascii=False),
                    saved["created_at"],
                    saved["updated_at"],
                ),
            )
        conn.commit()
        return saved


def delete_draft(draft_no: str) -> bool:
    with _lock:
        conn = _get_conn()
        cur = conn.execute("DELETE FROM drafts WHERE draft_no = ?", (draft_no,))
        conn.commit()
        return cur.rowcount > 0
