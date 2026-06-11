#!/usr/bin/env python3
import os, paramiko
PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")

REMOTE_PY = r"""
import json, sys
sys.path.insert(0, "/opt/product-listing/backend")
from env_loader import load_env
load_env()
from lingxing_client import LingxingClient
client = LingxingClient.from_env()

def children(uid):
    r = client.request("POST", "/basicOpen/openapi/publish/manage/categoryChildren", {
        "storeId": 12518, "categoryUniqueId": uid
    })
    return r["data"].get("categoryChildren") or []

# Automotive > Car Care > first child
uid = "107883919986130954"  # Car Care
items = children(uid)
print("Car Care children", [i["categoryName"] for i in items[:5]])
pest = next((i for i in items if "Pest" in i["categoryName"]), items[0])
print("selected", pest["categoryName"], pest["categoryUniqueId"])
leaf_items = children(pest["categoryUniqueId"])
print("leaf level", [(i["categoryName"], i.get("hasChildren"), i.get("productTypeOrigin"), i.get("browseNodeAttributes")) for i in leaf_items[:3]])
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.137.177.25", username="root", password=PASSWORD, timeout=20)
sftp = client.open_sftp()
with sftp.file("/tmp/lx_probe3.py", "w") as f:
    f.write(REMOTE_PY)
sftp.close()
_, o, _ = client.exec_command("python3.8 /tmp/lx_probe3.py", timeout=60)
print(o.read().decode())
