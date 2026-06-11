#!/usr/bin/env python3
"""Fix CRLF and restart listing service on Aliyun."""
import os
import sys

import paramiko

from deploy_config import LISTING_APP_PORT, REMOTE_DIR, REMOTE_HOST

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
PORT = LISTING_APP_PORT


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


def main() -> int:
    if not PASSWORD:
        print("Set REMOTE_SSH_PASSWORD")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(REMOTE_HOST, username="root", password=PASSWORD, timeout=20)
    try:
        upload_files = [
            "scripts/server_start.sh",
            "backend/category_service.py",
            "backend/schema_service.py",
            "backend/attribute_schema.py",
            "frontend/app.js",
            "frontend/index.html",
        ]
        sftp = client.open_sftp()
        for rel in upload_files:
            sftp.put(rel, f"{REMOTE_DIR}/{rel.replace(chr(92), '/')}")
            print("uploaded", rel)
        sftp.close()
        run(client, f"sed -i 's/\\r$//' {REMOTE_DIR}/scripts/server_start.sh")
        run(client, f"chmod +x {REMOTE_DIR}/scripts/server_start.sh")
        run(client, f"pkill -f '{REMOTE_DIR}/backend/app.py' || true")
        run(
            client,
            f"for pid in $(netstat -tlnp 2>/dev/null | grep ':{PORT} ' | awk '{{print $7}}' | cut -d/ -f1); do "
            f"kill -9 $pid 2>/dev/null || true; done",
        )
        run(
            client,
            f"cd {REMOTE_DIR} && setsid bash scripts/server_start.sh > logs/app.log 2>&1 < /dev/null & echo started",
            timeout=10,
        )
        run(client, "sleep 3")
        run(client, f"tail -n 12 {REMOTE_DIR}/logs/app.log")
        run(client, f"netstat -tlnp | grep {PORT} || true")
        run(
            client,
            f"curl -s 'http://127.0.0.1:{PORT}/api/categories/root?store_id=12518' | "
            "python3 -c \"import sys,json;d=json.load(sys.stdin);"
            "print('source=',d.get('source'));print('count=',len(d.get('data') or []))\"",
        )
        run(
            client,
            f"curl -s -o /dev/null -w 'image_upload:%{{http_code}}\\n' "
            f"-F 'file=@/etc/hosts;filename=test.jpg;type=image/jpeg' "
            f"http://127.0.0.1:{PORT}/api/images/upload",
        )
        print(f"\n刊登系统: http://{REMOTE_HOST}/listing/create-product")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
