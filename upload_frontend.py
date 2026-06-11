#!/usr/bin/env python3
"""Upload files to Aliyun and restart listing service on its own port."""
import os
import sys
import time

import paramiko

from deploy_config import LISTING_APP_PORT, REMOTE_DIR, REMOTE_HOST

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
FILES = [
    "backend/app.py",
    "backend/attribute_schema.py",
    "frontend/index.html",
    "frontend/app.js",
    "frontend/styles.css",
    "scripts/server_start.sh",
    "deploy_config.py",
]


def run(client, cmd, timeout=30):
    print("$", cmd)
    _, o, e = client.exec_command(cmd, timeout=timeout)
    out = o.read().decode(errors="replace").strip()
    err = e.read().decode(errors="replace").strip()
    if out:
        print(out)
    if err and "bash.cfg" not in err:
        print(err, file=sys.stderr)
    return out


def main():
    if not PASSWORD:
        print("Set REMOTE_SSH_PASSWORD")
        return 1

    port = LISTING_APP_PORT
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(REMOTE_HOST, username="root", password=PASSWORD, timeout=20)
    try:
        sftp = client.open_sftp()
        for rel in FILES:
            local = rel.replace("\\", "/")
            remote = f"{REMOTE_DIR}/{local}"
            sftp.put(local, remote)
            print("uploaded", rel)
        sftp.close()

        # 只重启刊登系统端口，不影响 8000 上的其他项目
        run(client, f"pkill -f '{REMOTE_DIR}/backend/app.py' || true")
        run(
            client,
            f"for pid in $(netstat -tlnp 2>/dev/null | grep ':{port} ' | awk '{{print $7}}' | cut -d/ -f1); do "
            f"kill -9 $pid 2>/dev/null || true; done",
        )
        time.sleep(1)
        run(
            client,
            f"grep -q '^APP_PORT=' {REMOTE_DIR}/.env 2>/dev/null || "
            f"echo 'APP_PORT={port}' >> {REMOTE_DIR}/.env",
        )
        run(
            client,
            f"sed -i 's/^APP_PORT=.*/APP_PORT={port}/' {REMOTE_DIR}/.env",
        )
        run(
            client,
            f"sed -i 's/\\r$//' {REMOTE_DIR}/scripts/server_start.sh",
        )
        run(
            client,
            f"cd {REMOTE_DIR} && chmod +x scripts/server_start.sh && "
            f"setsid bash scripts/server_start.sh > logs/app.log 2>&1 < /dev/null & echo restarted",
            timeout=10,
        )
        time.sleep(2)
        run(client, f"tail -n 5 {REMOTE_DIR}/logs/app.log")
        run(client, f"netstat -tlnp | grep {port} || true")
        run(
            client,
            f"curl -s --max-time 8 http://127.0.0.1:{port}/api/schema?product_type=AUTO_PART | "
            "python3.8 -c \"import sys,json;d=json.load(sys.stdin);"
            "print('ok', len(d.get('data',{}).get('attributes',[])))\"",
        )
        print(f"\n刊登系统: http://{REMOTE_HOST}:{port}/create-product")
        print(f"（补货等其他项目继续用 8000，互不干扰）")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
