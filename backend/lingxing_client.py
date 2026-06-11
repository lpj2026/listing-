from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.parse
from typing import Any

try:
    import requests
    from Crypto.Cipher import AES
except ImportError as exc:
    raise ImportError("缺少依赖，请运行: pip install requests pycryptodome") from exc


BASE_URL = os.environ.get("LINGXING_API_BASE", "https://openapi.lingxing.com")


class LingxingClient:
    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token: str | None = None

    @classmethod
    def from_env(cls) -> LingxingClient | None:
        app_id = os.environ.get("LINGXING_APP_ID", "").strip()
        app_secret = os.environ.get("LINGXING_APP_SECRET", "").strip()
        if not app_id or not app_secret:
            return None
        return cls(app_id, app_secret)

    def _aes_ecb_encrypt(self, text: str) -> str:
        cipher = AES.new(self.app_id.encode("utf-8"), AES.MODE_ECB)
        data = text.encode("utf-8")
        pad_len = 16 - len(data) % 16
        data += bytes([pad_len]) * pad_len
        return base64.b64encode(cipher.encrypt(data)).decode("utf-8")

    def _sign(self, params: dict[str, Any]) -> str:
        items = []
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            else:
                value_str = str(value)
            items.append(f"{key}={value_str}")
        md5_value = hashlib.md5("&".join(items).encode("utf-8")).hexdigest().upper()
        return self._aes_ecb_encrypt(md5_value)

    def get_token(self) -> str:
        url = (
            f"{BASE_URL}/api/auth-server/oauth/access-token"
            f"?appId={self.app_id}&appSecret={urllib.parse.quote(self.app_secret)}"
        )
        resp = requests.post(url, timeout=30)
        if resp.status_code == 403:
            raise RuntimeError("403 Forbidden：当前 IP 未加入领星白名单，请在领星后台添加本机公网 IP 或使用阿里云服务器 8.137.177.25 运行")
        resp.raise_for_status()
        payload = resp.json()
        if str(payload.get("code")) != "200":
            raise RuntimeError(f"获取 Token 失败: {payload.get('msg') or payload}")
        self.access_token = payload["data"]["access_token"]
        return self.access_token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.access_token:
            self.get_token()

        timestamp = str(int(time.time()))
        query_params: dict[str, Any] = {
            "app_key": self.app_id,
            "access_token": self.access_token,
            "timestamp": timestamp,
        }
        sign_params = dict(query_params)
        if body:
            sign_params.update(body)
        query_params["sign"] = self._sign(sign_params)

        url = f"{BASE_URL}{path}"
        if method.upper() == "GET":
            resp = requests.get(url, params=query_params, timeout=60)
        else:
            resp = requests.post(url, params=query_params, json=body or {}, timeout=60)

        try:
            payload = resp.json()
        except Exception as exc:
            raise RuntimeError(f"领星接口返回非 JSON: {resp.text[:200]}") from exc

        if str(payload.get("code")) in {"2001003"}:
            self.access_token = None
            self.get_token()
            return self.request(method, path, body)

        return payload
