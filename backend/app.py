from __future__ import annotations

import cgi
import json
import mimetypes
import os
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from env_loader import load_env

load_env()

from remote_proxy import remote_base

from category_service import list_categories, search_mock_categories
from image_service import resolve_upload_file, upload_image
from listing_service import find_listing_by_msku
from pair_service import pair_msku_to_local_sku
from publish_service import query_publish_result, submit_publish
from publish_worker import schedule_publish_poll, start_publish_worker
from schema_service import get_schema, get_variation_themes
from seller_service import list_stores
from sync_worker import check_listing_and_pair, pair_task_now, schedule_listing_sync, start_listing_sync_worker
from task_store import ACTIVE_TASK_STATUSES, apply_poll_result, load_tasks, save_tasks, update_task


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"
DRAFTS_FILE = DATA_DIR / "drafts.json"
TASKS_FILE = DATA_DIR / "tasks.json"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_data_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "uploads").mkdir(exist_ok=True)
    for file_path in [DRAFTS_FILE, TASKS_FILE]:
        if not file_path.exists():
            file_path.write_text("[]", encoding="utf-8")


def load_records(file_path: Path) -> list[dict[str, Any]]:
    ensure_data_files()
    raw = file_path.read_text(encoding="utf-8")
    return json.loads(raw) if raw.strip() else []


def save_records(file_path: Path, records: list[dict[str, Any]]) -> None:
    ensure_data_files()
    file_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def next_no(prefix: str, records: list[dict[str, Any]], key: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = sum(1 for record in records if str(record.get(key, "")).startswith(f"{prefix}-{today}"))
    return f"{prefix}-{today}-{count + 1:04d}"


def json_response(handler: SimpleHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_body(handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw) if raw else {}


def read_upload_file(handler: SimpleHTTPRequestHandler) -> tuple[bytes, str, str]:
    content_type = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        raise ValueError("请使用 multipart/form-data 上传图片")

    form = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": handler.headers.get("Content-Length", "0"),
        },
    )
    field = form["file"] if "file" in form else None
    if field is None or not getattr(field, "file", None):
        raise ValueError("缺少 file 字段")

    data = field.file.read()
    filename = getattr(field, "filename", "") or "image.jpg"
    mime = getattr(field, "type", "") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return data, filename, mime


def binary_response(handler: SimpleHTTPRequestHandler, data: bytes, content_type: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "public, max-age=86400")
    handler.end_headers()
    handler.wfile.write(data)


class ProductHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{now_text()}] {self.address_string()} {format % args}")

    def do_GET(self) -> None:
        try:
            self._do_get()
        except Exception as exc:
            print(f"[ERROR] GET {self.path}: {exc}")
            json_response(self, {"code": 0, "message": str(exc)}, status=500)

    def _do_get(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/stores":
            json_response(self, list_stores())
            return

        if path == "/api/categories/root":
            query = parse_qs(parsed.query)
            store_id = int(query.get("store_id", ["0"])[0] or 0) or None
            json_response(self, list_categories(store_id=store_id, parent_id=None))
            return

        if path == "/api/categories/children":
            query = parse_qs(parsed.query)
            store_id = int(query.get("store_id", ["0"])[0] or 0) or None
            parent_id = query.get("parent_id", [""])[0] or None
            if not parent_id:
                json_response(self, {"code": 0, "message": "缺少 parent_id"}, status=400)
                return
            json_response(self, list_categories(store_id=store_id, parent_id=parent_id))
            return

        if path == "/api/categories/search":
            query = parse_qs(parsed.query)
            keyword = query.get("q", [""])[0]
            json_response(self, {"data": search_mock_categories(keyword)})
            return

        if path == "/api/schema":
            query = parse_qs(parsed.query)
            product_type = query.get("product_type", ["AUTO_PART"])[0]
            marketplace_id = query.get("marketplace_id", ["ATVPDKIKX0DER"])[0]
            json_response(self, get_schema(marketplace_id, product_type))
            return

        if path == "/api/variation-themes":
            query = parse_qs(parsed.query)
            product_type = query.get("product_type", ["AUTO_PART"])[0]
            marketplace_id = query.get("marketplace_id", ["ATVPDKIKX0DER"])[0]
            json_response(self, get_variation_themes(marketplace_id, product_type))
            return

        if path == "/api/drafts":
            drafts = sorted(load_records(DRAFTS_FILE), key=lambda item: item.get("updated_at", ""), reverse=True)
            json_response(self, {"data": drafts})
            return

        if path.startswith("/api/drafts/"):
            draft_no = path.rsplit("/", 1)[-1]
            draft = next((item for item in load_records(DRAFTS_FILE) if item.get("draft_no") == draft_no), None)
            if draft is None:
                json_response(self, {"code": 0, "message": "草稿不存在"}, status=404)
                return
            json_response(self, {"code": 1, "data": draft})
            return

        if path.startswith("/api/publish/result/"):
            task_no = path.rsplit("/", 1)[-1]
            task = next((item for item in load_tasks() if item.get("task_no") == task_no), None)
            if task is None:
                json_response(self, {"code": 0, "message": "任务不存在"}, status=404)
                return
            record_unique_id = task.get("record_unique_id") or ""
            if not record_unique_id:
                json_response(self, {"code": 0, "message": "任务尚未提交领星刊登"}, status=400)
                return
            try:
                result = query_publish_result(
                    record_unique_id=record_unique_id,
                    store_id=int(task.get("store_id") or 0) or None,
                    sku=str(task.get("msku") or ""),
                )
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=502)
                return

            def updater(item: dict[str, Any]) -> None:
                apply_poll_result(item, result)

            task = update_task(task_no, updater)
            if task and task.get("status") == "LISTING_SYNCING":
                schedule_listing_sync(task_no)
            json_response(
                self,
                {
                    "code": 1,
                    "message": task["status_text"] if task else "已刷新",
                    "data": {
                        "task": task,
                        "result": result,
                    },
                },
            )
            return

        if path.startswith("/api/tasks/") and path.endswith("/sync"):
            task_no = path.rsplit("/", 2)[-2]
            try:
                result = check_listing_and_pair(task_no)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=502)
                return
            message = "Listing 已同步" if result.get("found") else "Listing 尚未出现"
            json_response(self, {"code": 1, "message": message, "data": result})
            return

        if path.startswith("/api/tasks/") and path.endswith("/pair"):
            task_no = path.rsplit("/", 2)[-2]
            try:
                result = pair_task_now(task_no)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            json_response(self, {"code": 1, "message": "SKU 配对成功", "data": result})
            return

        if path == "/api/tasks":
            tasks = sorted(load_tasks(), key=lambda item: item.get("created_at", ""), reverse=True)
            json_response(
                self,
                {
                    "data": tasks,
                    "polling": sum(1 for item in tasks if item.get("status") in ACTIVE_TASK_STATUSES),
                },
            )
            return

        if path.startswith("/uploads/"):
            relative = path[len("/uploads/"):] if path.startswith("/uploads/") else path
            file_path = resolve_upload_file(relative)
            if file_path is None:
                json_response(self, {"code": 0, "message": "图片不存在"}, status=404)
                return
            mime, _ = mimetypes.guess_type(str(file_path))
            binary_response(self, file_path.read_bytes(), mime or "application/octet-stream")
            return

        if path in {"/", "/create-product", "/create_product"}:
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        try:
            self._do_post()
        except Exception as exc:
            print(f"[ERROR] POST {self.path}: {exc}")
            json_response(self, {"code": 0, "message": str(exc)}, status=500)

    def _do_post(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/tasks/") and path.endswith("/sync"):
            task_no = path.rsplit("/", 2)[-2]
            try:
                result = check_listing_and_pair(task_no)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=502)
                return
            message = "Listing 已同步" if result.get("found") else "Listing 尚未出现"
            json_response(self, {"code": 1, "message": message, "data": result})
            return

        if path.startswith("/api/tasks/") and path.endswith("/pair"):
            task_no = path.rsplit("/", 2)[-2]
            try:
                result = pair_task_now(task_no)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            json_response(self, {"code": 1, "message": "SKU 配对成功", "data": result})
            return

        if parsed.path == "/api/images/upload":
            try:
                data, filename, mime = read_upload_file(self)
                result = upload_image(data, filename, mime)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            provider = "OSS" if result["provider"] == "oss" else "服务器图床"
            json_response(
                self,
                {
                    "code": 1,
                    "message": f"图片已上传到{provider}",
                    "data": result,
                },
            )
            return

        if parsed.path == "/api/drafts":
            payload = read_body(self)
            drafts = load_records(DRAFTS_FILE)
            draft_no = payload.get("draft_no")
            existing = next((item for item in drafts if item.get("draft_no") == draft_no), None)

            if existing:
                existing.update(payload)
                existing["updated_at"] = now_text()
                saved = existing
            else:
                saved = {
                    **payload,
                    "draft_no": next_no("DRAFT", drafts, "draft_no"),
                    "created_at": now_text(),
                    "updated_at": now_text(),
                }
                drafts.append(saved)

            save_records(DRAFTS_FILE, drafts)
            json_response(
                self,
                {
                    "code": 1,
                    "message": "草稿已保存",
                    "data": saved,
                },
            )
            return

        if parsed.path == "/api/proxy/publish":
            payload = read_body(self)
            try:
                result = submit_publish(payload)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            json_response(self, {"code": 1, "message": "ok", "data": result})
            return

        if parsed.path == "/api/proxy/publish/query":
            payload = read_body(self)
            try:
                result = query_publish_result(
                    record_unique_id=payload.get("record_unique_id"),
                    store_id=int(payload.get("store_id") or 0) or None,
                    sku=str(payload.get("sku") or "") or None,
                    offset=int(payload.get("offset") or 0),
                    length=int(payload.get("length") or 20),
                )
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            json_response(self, {"code": 1, "message": "ok", "data": result})
            return

        if parsed.path == "/api/proxy/listing/find":
            payload = read_body(self)
            try:
                item = find_listing_by_msku(
                    int(payload.get("store_id") or 0),
                    str(payload.get("msku") or ""),
                )
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            json_response(self, {"code": 1, "message": "ok", "data": item})
            return

        if parsed.path == "/api/proxy/pair":
            payload = read_body(self)
            try:
                result = pair_msku_to_local_sku(
                    seller_id=str(payload.get("seller_id") or ""),
                    marketplace_id=str(payload.get("marketplace_id") or ""),
                    msku=str(payload.get("msku") or ""),
                    local_sku=str(payload.get("local_sku") or ""),
                    is_sync_pic=int(payload.get("is_sync_pic") or 1),
                )
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return
            json_response(self, {"code": 1, "message": "ok", "data": result})
            return

        if parsed.path == "/api/publish/preview":
            payload = read_body(self)
            tasks = load_records(TASKS_FILE)
            task = {
                "task_no": next_no("TASK", tasks, "task_no"),
                "draft_no": payload.get("draft_no") or "",
                "store_id": payload.get("store_id"),
                "store_name": payload.get("store_name"),
                "marketplace_id": payload.get("marketplace_id"),
                "msku": payload.get("msku") or payload.get("raw_form", {}).get("seller_sku", ""),
                "product_type": payload.get("product_type"),
                "status": "READY",
                "status_text": "待提交领星",
                "failure_reason": "",
                "record_unique_id": "",
                "poll_attempt": 0,
                "created_at": now_text(),
                "payload": payload,
            }
            tasks.append(task)
            save_records(TASKS_FILE, tasks)
            json_response(
                self,
                {
                    "code": 1,
                    "message": "已生成本地刊登任务（未调用领星 API）",
                    "data": task,
                },
            )
            return

        if parsed.path == "/api/publish":
            payload = read_body(self)
            tasks = load_records(TASKS_FILE)
            try:
                publish_result = submit_publish(payload)
            except Exception as exc:
                json_response(self, {"code": 0, "message": str(exc)}, status=400)
                return

            task = {
                "task_no": next_no("TASK", tasks, "task_no"),
                "draft_no": payload.get("draft_no") or "",
                "store_id": payload.get("store_id"),
                "store_name": payload.get("store_name"),
                "seller_id": payload.get("seller_id") or "",
                "marketplace_id": payload.get("marketplace_id"),
                "msku": payload.get("msku") or payload.get("raw_form", {}).get("seller_sku", ""),
                "local_sku": payload.get("local_sku") or payload.get("raw_form", {}).get("local_sku", ""),
                "product_type": payload.get("product_type"),
                "status": "SUBMITTED",
                "status_text": "已提交领星，自动轮询中",
                "failure_reason": "",
                "record_unique_id": publish_result["record_unique_id"],
                "poll_attempt": 0,
                "sync_attempt": 0,
                "sku_paired": False,
                "created_at": now_text(),
                "payload": payload,
                "publish_request": publish_result["request"],
                "publish_response": publish_result["response"],
            }
            tasks.append(task)
            save_records(TASKS_FILE, tasks)
            schedule_publish_poll(task["task_no"])
            json_response(
                self,
                {
                    "code": 1,
                    "message": "已提交领星刊登，系统将自动查询结果",
                    "data": task,
                },
            )
            return

        json_response(self, {"code": 0, "message": "接口不存在"}, status=404)


class ReuseHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def run(host: str | None = None, port: int | None = None) -> None:
    ensure_data_files()
    start_publish_worker()
    start_listing_sync_worker()
    host = host or os.environ.get("APP_HOST", "127.0.0.1")
    port = int(port or os.environ.get("APP_PORT", "8001"))
    server = ReuseHTTPServer((host, port), ProductHandler)
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print("Product listing system running")
    print(f"Local:  http://{display_host}:{port}/create-product")
    public_host = os.environ.get("PUBLIC_HOST", "").strip()
    if public_host:
        print(f"Public: http://{public_host}:{port}/create-product")
    proxy = remote_base()
    if proxy:
        print(f"Proxy:  {proxy} (领星 API 403 时自动转发)")
    server.serve_forever()


if __name__ == "__main__":
    run()
