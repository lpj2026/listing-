#!/usr/bin/env python3
import os
import sys

import paramiko

from deploy_config import LISTING_APP_PORT, REMOTE_DIR, REMOTE_HOST

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
PY = "python3.8"
UPLOAD = [
    "backend/category_service.py",
    "backend/stores_data.py",
    "backend/app.py",
    "backend/attribute_schema.py",
    "frontend/index.html",
    "frontend/app.js",
    "frontend/styles.css",
    "scripts/server_start.sh",
    "deploy_config.py",
]


def run(client, cmd, timeout=60):
    print("$", cmd)
    _, o, e = client.exec_command(cmd, timeout=timeout)
    out = o.read().decode(errors="replace")
    err = e.read().decode(errors="replace")
    if out.strip():
        print(out.rstrip())
    if err.strip() and "bash.cfg" not in err:
        print(err.rstrip(), file=sys.stderr)
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
        for rel in UPLOAD:
            sftp.put(rel, f"{REMOTE_DIR}/{rel.replace(chr(92), '/')}")
        sftp.close()

        run(client, f"pkill -f '{REMOTE_DIR}/backend/app.py' || true")
        run(
            client,
            f"for pid in $(netstat -tlnp 2>/dev/null | grep ':{port} ' | awk '{{print $7}}' | cut -d/ -f1); do "
            f"kill -9 $pid 2>/dev/null || true; done",
        )
        run(
            client,
            f"grep -q '^APP_PORT=' {REMOTE_DIR}/.env 2>/dev/null || "
            f"echo 'APP_PORT={port}' >> {REMOTE_DIR}/.env",
        )
        run(client, f"sed -i 's/^APP_PORT=.*/APP_PORT={port}/' {REMOTE_DIR}/.env")
        run(
            client,
            f"cd {REMOTE_DIR} && chmod +x scripts/server_start.sh && "
            f"setsid bash scripts/server_start.sh > logs/app.log 2>&1 < /dev/null & echo started",
            timeout=10,
        )
        run(client, "sleep 2")
        run(client, f"tail -n 8 {REMOTE_DIR}/logs/app.log")
        run(client, f"netstat -tlnp | grep {port} || true")
        run(
            client,
            f"curl -s http://127.0.0.1:{port}/api/categories/root?store_id=12518 | {PY} -c "
            "\"import sys,json;d=json.load(sys.stdin);print('source=',d.get('source'));print('count=',len(d.get('data') or []))\"",
        )
        print(f"\n刊登系统: http://{REMOTE_HOST}:{port}/create-product")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
