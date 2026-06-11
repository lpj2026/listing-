#!/usr/bin/env python3
import os
import paramiko

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")

cmds = [
    "netstat -tlnp | grep 8000 || true",
    "ps aux | grep python | grep -v grep || true",
    "curl -s -w '\\nHTTP:%{http_code}\\n' http://127.0.0.1:8000/create-product | head -c 200",
    "echo '---'",
    "curl -s -w '\\nHTTP:%{http_code}\\n' http://127.0.0.1:8000/create_product | head -c 200",
    "tail -n 8 /opt/product-listing/logs/app.log 2>/dev/null || echo no-log",
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.137.177.25", username="root", password=PASSWORD, timeout=20)
for cmd in cmds:
    print("===", cmd)
    _, o, _ = client.exec_command(cmd, timeout=30)
    print(o.read().decode(errors="replace"))
client.close()
