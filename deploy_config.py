"""部署配置：刊登系统与补货系统分端口，避免共用同一访问地址。"""
from __future__ import annotations

import os

REMOTE_HOST = os.environ.get("REMOTE_HOST", "8.137.177.25")
REMOTE_USER = os.environ.get("REMOTE_USER", "root")
REMOTE_DIR = os.environ.get("REMOTE_DIR", "/opt/product-listing")

# 补货等项目常用 8000；刊登系统默认 8001，可通过 APP_PORT 覆盖
LISTING_APP_PORT = os.environ.get("APP_PORT", "8001")
