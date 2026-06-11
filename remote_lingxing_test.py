#!/usr/bin/env python3
"""通过阿里云服务器远程执行领星 API 测试"""

import base64
import hashlib
import json
import time
import urllib.parse

import paramiko

HOST = "8.137.177.25"
USER = "root"
PASSWORD = ""  # 通过环境变量 REMOTE_SSH_PASSWORD 传入
APP_ID = ""  # 通过环境变量 LINGXING_APP_ID 传入
APP_SECRET = ""  # 通过环境变量 LINGXING_APP_SECRET 传入
BASE = "https://openapi.lingxing.com"


def run(client, cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


REMOTE_TEST_TEMPLATE = '''
import base64, hashlib, json, time, urllib.parse, sys
try:
    import requests
    from Crypto.Cipher import AES
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests", "pycryptodome"])
    import requests
    from Crypto.Cipher import AES

APP_ID = "__APP_ID__"
APP_SECRET = "__APP_SECRET__"
BASE = "__BASE__"

def aes_encrypt(text, key):
    cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
    data = text.encode("utf-8")
    pad = 16 - len(data) % 16
    data += bytes([pad]) * pad
    return base64.b64encode(cipher.encrypt(data)).decode("utf-8")

def sign(params, app_id):
    parts = []
    for k in sorted(params.keys()):
        v = params[k]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        else:
            v = str(v)
        parts.append("%s=%s" % (k, v))
    raw = "&".join(parts)
    md5v = hashlib.md5(raw.encode("utf-8")).hexdigest().upper()
    return aes_encrypt(md5v, app_id)

def get_token():
    url = BASE + "/api/auth-server/oauth/access-token?appId=" + APP_ID + "&appSecret=" + urllib.parse.quote(APP_SECRET)
    r = requests.post(url, timeout=30)
    data = r.json()
    if str(data.get("code")) != "200":
        raise Exception("token failed: " + json.dumps(data, ensure_ascii=False))
    return data["data"]["access_token"]

def api(method, path, body=None):
    token = get_token()
    ts = str(int(time.time()))
    q = {"app_key": APP_ID, "access_token": token, "timestamp": ts}
    sp = dict(q)
    if body:
        sp.update(body)
    q["sign"] = sign(sp, APP_ID)
    url = BASE + path
    if method == "GET":
        return requests.get(url, params=q, timeout=30).json()
    return requests.post(url, params=q, json=body or {}, timeout=30).json()

results = []

# 1 token
try:
    t = get_token()
    results.append({"test": "Token", "ok": True, "msg": "ok, prefix=" + t[:8]})
except Exception as e:
    results.append({"test": "Token", "ok": False, "msg": str(e)})

# 2 sellers
try:
    data = api("GET", "/erp/sc/data/seller/lists")
    sellers = data.get("data", [])
    results.append({
        "test": "Sellers",
        "ok": data.get("code") == 0,
        "msg": "count=%d" % len(sellers),
        "sample": [{"sid": s.get("sid"), "name": s.get("name"), "country": s.get("country")} for s in sellers[:5]],
    })
    first_sid = sellers[0]["sid"] if sellers else None
except Exception as e:
    results.append({"test": "Sellers", "ok": False, "msg": str(e)})
    first_sid = None

# 3 listing query
if first_sid:
    try:
        data = api("POST", "/erp/sc/data/mws/listing", {"sid": first_sid, "is_pair": 2, "offset": 0, "length": 5})
        listings = data.get("data", [])
        results.append({
            "test": "Listing query",
            "ok": data.get("code") == 0,
            "msg": "count=%d" % len(listings),
            "sample": [{"msku": i.get("seller_sku"), "asin": i.get("asin"), "title": (i.get("item_name") or "")[:40]} for i in listings[:3]],
        })
    except Exception as e:
        results.append({"test": "Listing query", "ok": False, "msg": str(e)})

# 4 local products
try:
    data = api("POST", "/erp/sc/routing/data/local_inventory/productList", {"offset": 0, "length": 5})
    products = data.get("data", [])
    results.append({
        "test": "Local products",
        "ok": data.get("code") == 0,
        "msg": "count=%d" % len(products),
        "sample": [{"sku": p.get("sku"), "name": p.get("product_name")} for p in products[:3]],
    })
except Exception as e:
    results.append({"test": "Local products", "ok": False, "msg": str(e)})

print(json.dumps(results, ensure_ascii=False, indent=2))
'''

REMOTE_TEST = (
    REMOTE_TEST_TEMPLATE.replace("__APP_ID__", APP_ID)
    .replace("__APP_SECRET__", APP_SECRET)
    .replace("__BASE__", BASE)
)


def main():
    import os

    global HOST, USER, PASSWORD, APP_ID, APP_SECRET
    PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", PASSWORD)
    APP_ID = os.environ.get("LINGXING_APP_ID", APP_ID)
    APP_SECRET = os.environ.get("LINGXING_APP_SECRET", APP_SECRET)
    if not all([PASSWORD, APP_ID, APP_SECRET]):
        raise SystemExit("请设置 REMOTE_SSH_PASSWORD / LINGXING_APP_ID / LINGXING_APP_SECRET")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=15)

    print("=== Server public IP ===")
    _, out, _ = run(client, "curl -s https://api.ipify.org || curl -s ifconfig.me")
    print(out.strip())

    print("\n=== Python version ===")
    _, out, _ = run(client, "python3 --version 2>&1 || python --version 2>&1")
    print(out.strip())

    sftp = client.open_sftp()
    with sftp.file("/tmp/lx_api_test.py", "w") as remote:
        remote.write(REMOTE_TEST)
    sftp.close()

    print("\n=== API tests from Aliyun server ===")
    _, out, err = run(client, "python3 /tmp/lx_api_test.py 2>&1 || python /tmp/lx_api_test.py 2>&1", timeout=180)
    print(out)
    if err.strip() and "Operation not permitted" not in err:
        print("STDERR:", err[:500])

    client.close()


if __name__ == "__main__":
    main()
