#!/usr/bin/env python3
"""测试领星刊登开放 API（5步流程相关接口）"""

import base64
import hashlib
import json
import os
import time
import urllib.parse

import paramiko

HOST = os.environ.get("REMOTE_HOST", "8.137.177.25")
USER = os.environ.get("REMOTE_USER", "root")
PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
APP_ID = os.environ.get("LINGXING_APP_ID", "")
APP_SECRET = os.environ.get("LINGXING_APP_SECRET", "")
BASE = "https://openapi.lingxing.com"

REMOTE_SCRIPT = r"""
import base64, hashlib, json, time, urllib.parse, sys
import requests
from Crypto.Cipher import AES

APP_ID = "__APP_ID__"
APP_SECRET = "__APP_SECRET__"
BASE = "__BASE__"

def aes_encrypt(text, key):
    cipher = AES.new(key.encode(), AES.MODE_ECB)
    data = text.encode()
    pad = 16 - len(data) % 16
    data += bytes([pad]) * pad
    return base64.b64encode(cipher.encrypt(data)).decode()

def sign(params, app_id):
    parts = []
    for k in sorted(params):
        v = params[k]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        else:
            v = str(v)
        parts.append("%s=%s" % (k, v))
    md5v = hashlib.md5("&".join(parts).encode()).hexdigest().upper()
    return aes_encrypt(md5v, app_id)

def get_token():
    url = BASE + "/api/auth-server/oauth/access-token?appId=" + APP_ID + "&appSecret=" + urllib.parse.quote(APP_SECRET)
    r = requests.post(url, timeout=30)
    data = r.json()
    if str(data.get("code")) != "200":
        raise Exception(json.dumps(data, ensure_ascii=False))
    return data["data"]["access_token"]

def call(method, path, body=None):
    token = get_token()
    ts = str(int(time.time()))
    q = {"app_key": APP_ID, "access_token": token, "timestamp": ts}
    sp = dict(q)
    if body:
        sp.update(body)
    q["sign"] = sign(sp, APP_ID)
    url = BASE + path
    if method == "GET":
        r = requests.get(url, params=q, timeout=60)
    else:
        r = requests.post(url, params=q, json=body or {}, timeout=60)
    try:
        return {"path": path, "http": r.status_code, "data": r.json()}
    except Exception:
        return {"path": path, "http": r.status_code, "text": r.text[:500]}

# 先拿一个 US 店铺 sid
sellers = call("GET", "/erp/sc/data/seller/lists")
us_sid = None
us_seller = None
for s in sellers.get("data", {}).get("data", []):
    if s.get("country") in ("美国", "US", "USA") or "US" in (s.get("name") or ""):
        us_sid = s.get("sid")
        us_seller = s
        break
if not us_sid and sellers.get("data", {}).get("data"):
    us_sid = sellers["data"]["data"][0]["sid"]
    us_seller = sellers["data"]["data"][0]

results = []
results.append({"step": "0-sellers", "sid": us_sid, "shop": us_seller})

# 步骤一：根分类
paths = [
    ("POST", "/basicOpen/openapi/publish/manage/categoryRoot", {"sid": us_sid}),
    ("POST", "/erp/sc/basicOpen/openapi/publish/manage/categoryRoot", {"sid": us_sid}),
    ("POST", "/openapi/basicOpen/publish/manage/categoryRoot", {"sid": us_sid}),
]

for method, path, body in paths:
    resp = call(method, path, body)
    code = resp.get("data", {}).get("code")
    payload = resp.get("data", {}).get("data")
    if isinstance(payload, list):
        sample, count = payload[:2], len(payload)
    elif isinstance(payload, dict):
        sample, count = payload, 1
    else:
        sample, count = None, 0
    results.append({
        "step": "1-categoryRoot",
        "path": path,
        "code": code,
        "msg": resp.get("data", {}).get("msg") or resp.get("data", {}).get("message"),
        "count": count,
        "sample": sample,
        "http": resp.get("http"),
    })
    if code == 0 or str(code) == "0":
        break

# 步骤五：查询刊登结果（空查，验证接口权限）
for path in [
    "/listing/publish/openapi/amazon/product/list",
    "/erp/sc/listing/publish/openapi/amazon/product/list",
]:
    body = {"store_id": us_sid, "offset": 0, "length": 5}
    resp = call("POST", path, body)
    code = resp.get("data", {}).get("code")
    payload = resp.get("data", {}).get("data")
    count = len(payload) if isinstance(payload, list) else (1 if payload else 0)
    results.append({
        "step": "5-publish-list",
        "path": path,
        "code": code,
        "msg": resp.get("data", {}).get("msg") or resp.get("data", {}).get("message"),
        "count": count,
        "http": resp.get("http"),
    })
    if code == 0 or str(code) == "0":
        break

print(json.dumps(results, ensure_ascii=False, indent=2))
"""


def main():
    if not all([PASSWORD, APP_ID, APP_SECRET]):
        raise SystemExit("请设置 REMOTE_SSH_PASSWORD / LINGXING_APP_ID / LINGXING_APP_SECRET")

    script = (
        REMOTE_SCRIPT.replace("__APP_ID__", APP_ID)
        .replace("__APP_SECRET__", APP_SECRET)
        .replace("__BASE__", BASE)
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=15)

    sftp = client.open_sftp()
    with sftp.file("/tmp/lx_publish_test.py", "w") as f:
        f.write(script)
    sftp.close()

    stdin, stdout, stderr = client.exec_command(
        "python3 /tmp/lx_publish_test.py 2>&1", timeout=180
    )
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("STDERR:", err[:500])
    client.close()


if __name__ == "__main__":
    main()
