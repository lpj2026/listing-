#!/usr/bin/env python3
import os
import time
import paramiko

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
REMOTE = "/opt/product-listing"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.137.177.25", username="root", password=PASSWORD, timeout=20)

def run(cmd):
    print("$", cmd)
    _, o, e = client.exec_command(cmd, timeout=60)
    out = o.read().decode(errors="replace")
    err = e.read().decode(errors="replace")
    if out.strip():
        print(out.rstrip())
    if err.strip() and "bash.cfg" not in err:
        print(err.rstrip())

run("ls -l /proc/$(netstat -tlnp | grep ':8000 ' | awk '{print $7}' | cut -d/ -f1)/cwd 2>/dev/null || true")
run("tr '\\0' ' ' < /proc/$(netstat -tlnp | grep ':8000 ' | awk '{print $7}' | cut -d/ -f1)/cmdline 2>/dev/null; echo")
run("fuser -k 8000/tcp 2>/dev/null || true")
run("pkill -9 -f 'python3 app.py' || true")
run("pkill -9 -f '/opt/product-listing/backend/app.py' || true")
time.sleep(2)
client.exec_command(f"cd {REMOTE} && setsid bash scripts/server_start.sh >> logs/app.log 2>&1 < /dev/null &")
time.sleep(4)
run("tr '\\0' ' ' < /proc/$(netstat -tlnp | grep ':8000 ' | awk '{print $7}' | cut -d/ -f1)/cmdline 2>/dev/null; echo")
run("curl -s http://127.0.0.1:8000/create-product | head -c 150")
run("curl -s http://127.0.0.1:8000/create_product | head -c 150")
client.close()
