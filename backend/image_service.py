from __future__ import annotations

import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT_DIR / "data" / "uploads"

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def max_upload_bytes() -> int:
    raw = os.environ.get("IMAGE_MAX_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_BYTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_BYTES


def public_base_url() -> str:
    explicit = os.environ.get("IMAGE_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    host = os.environ.get("PUBLIC_HOST", "").strip().rstrip("/")
    if host:
        if host.startswith("http://") or host.startswith("https://"):
            return host
        return f"http://{host}/listing"
    return "http://127.0.0.1:8001"


def _normalize_ext(filename: str, content_type: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if ext == ".jpeg" else ext
    return ALLOWED_MIME.get(content_type, ".jpg")


def _oss_configured() -> bool:
    required = ("OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET", "OSS_BUCKET", "OSS_ENDPOINT")
    return all(os.environ.get(key, "").strip() for key in required)


def _upload_to_oss(data: bytes, object_key: str, content_type: str) -> str:
    try:
        import oss2
    except ImportError as exc:
        raise RuntimeError("未安装 oss2，请运行: pip install oss2") from exc

    auth = oss2.Auth(
        os.environ["OSS_ACCESS_KEY_ID"].strip(),
        os.environ["OSS_ACCESS_KEY_SECRET"].strip(),
    )
    bucket = oss2.Bucket(
        auth,
        os.environ["OSS_ENDPOINT"].strip(),
        os.environ["OSS_BUCKET"].strip(),
    )
    bucket.put_object(object_key, data, headers={"Content-Type": content_type})

    public_base = os.environ.get("OSS_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if public_base:
        return f"{public_base}/{object_key}"
    endpoint = os.environ["OSS_ENDPOINT"].strip()
    if endpoint.startswith("https://"):
        endpoint = endpoint[8:]
    elif endpoint.startswith("http://"):
        endpoint = endpoint[7:]
    bucket_name = os.environ["OSS_BUCKET"].strip()
    return f"https://{bucket_name}.{endpoint}/{object_key}"


def _upload_to_local(data: bytes, filename: str, content_type: str) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    day_dir = UPLOAD_DIR / day
    day_dir.mkdir(parents=True, exist_ok=True)

    ext = _normalize_ext(filename, content_type)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = day_dir / stored_name
    target.write_bytes(data)
    return f"{public_base_url()}/uploads/{day}/{stored_name}"


def upload_image(data: bytes, filename: str, content_type: str) -> dict[str, Any]:
    if not data:
        raise ValueError("图片文件为空")

    limit = max_upload_bytes()
    if len(data) > limit:
        raise ValueError(f"图片过大，最大允许 {limit // 1024 // 1024}MB")

    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime not in ALLOWED_MIME:
        guessed, _ = mimetypes.guess_type(filename or "")
        mime = (guessed or "").lower()
    if mime not in ALLOWED_MIME:
        raise ValueError("仅支持 JPG / PNG / WEBP / GIF 图片")

    if _oss_configured():
        prefix = os.environ.get("OSS_PREFIX", "listing-images/").strip() or "listing-images/"
        if not prefix.endswith("/"):
            prefix += "/"
        day = datetime.now().strftime("%Y%m%d")
        ext = _normalize_ext(filename, mime)
        object_key = f"{prefix}{day}/{uuid.uuid4().hex}{ext}"
        url = _upload_to_oss(data, object_key, mime)
        provider = "oss"
    else:
        url = _upload_to_local(data, filename, mime)
        provider = "local"

    return {
        "url": url,
        "provider": provider,
        "content_type": mime,
        "size": len(data),
    }


def resolve_upload_file(relative_path: str) -> Path | None:
    clean = relative_path.replace("\\", "/").strip("/")
    if not clean or ".." in clean.split("/"):
        return None
    candidate = (UPLOAD_DIR / clean).resolve()
    try:
        candidate.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None
