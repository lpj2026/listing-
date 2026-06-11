#!/usr/bin/env python3
"""Fix and restart service on Aliyun after deploy."""

from __future__ import annotations

import os
import sys

import paramiko

HOST = os.environ.get("REMOTE_HOST", "8.137.177.25")
USER = os.environ.get("REMOTE_USER", "root")
PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
REMOTE_DIR = "/opt/product-listing"


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 300) -> tuple[int, str]:
    print(f"$ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip() and "bash.cfg" not in err:
        print(err.rstrip(), file=sys.stderr)
    return code, out


def detect_python(client: paramiko.SSHClient) -> str:
    for py in ("python3.11", "python3.10", "python3.9", "python3.8"):
        code, out = run(client, f"command -v {py} || true")
        if code == 0 and py in out:
            return py
    return ""


def install_python(client: paramiko.SSHClient) -> str:
    py = detect_python(client)
    if py:
        return py

    print("Installing python39 ...")
    run(
        client,
        "dnf install -y python39 python39-pip "
        "--disablerepo='mysql*' --setopt=strict=0 2>&1 | tail -30",
        timeout=600,
    )
    py = detect_python(client)
    if py:
        return py

    print("Trying python38 ...")
    run(
        client,
        "dnf install -y python38 python38-pip "
        "--disablerepo='mysql*' --setopt=strict=0 2>&1 | tail -30",
        timeout=600,
    )
    return detect_python(client)


def main() -> int:
    if not PASSWORD:
        print("Set REMOTE_SSH_PASSWORD")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=20)

    try:
        py = install_python(client)
        if not py:
            print("No Python 3.8+ found. Installing via module ...")
            run(client, "dnf module list python39 2>&1 | head -10")
            return 1

        run(client, f"{py} --version")
        run(client, f"{py} -m pip install -q --upgrade 'pip<24'")
        run(
            client,
            f"cd {REMOTE_DIR} && {py} -m pip install -q 'requests>=2.27.0' 'pycryptodome>=3.15.0'",
        )

        # Upload latest stores_data fix if present locally
        local_stores = os.path.join(os.path.dirname(__file__), "backend", "stores_data.py")
        if os.path.exists(local_stores):
            sftp = client.open_sftp()
            sftp.put(local_stores, f"{REMOTE_DIR}/backend/stores_data.py")
            sftp.close()

        start_sh = (
            "#!/bin/bash\n"
            f"cd {REMOTE_DIR}/backend\n"
            f"mkdir -p {REMOTE_DIR}/logs {REMOTE_DIR}/data\n"
            "export APP_HOST=0.0.0.0\n"
            "export APP_PORT=8000\n"
            f"exec {py} -u app.py\n"
        )
        sftp = client.open_sftp()
        with sftp.file(f"{REMOTE_DIR}/scripts/server_start.sh", "w") as f:
            f.write(start_sh)
        sftp.close()
        run(client, f"chmod +x {REMOTE_DIR}/scripts/server_start.sh")

        run(
            client,
            "for pid in $(netstat -tlnp 2>/dev/null | grep ':8000 ' | awk '{print $7}' | cut -d/ -f1); do kill -9 $pid 2>/dev/null || true; done",
        )
        run(
            client,
            f"cd {REMOTE_DIR} && nohup bash scripts/server_start.sh > logs/app.log 2>&1 & echo $! > app.pid && sleep 4 && cat app.pid",
        )
        run(client, f"tail -n 25 {REMOTE_DIR}/logs/app.log")
        run(client, "netstat -tlnp | grep 8000 || true")

        verify_cmd = (
            "curl -s 'http://127.0.0.1:8000/api/categories/root?store_id=12518' | "
            f"{py} -c \"import sys,json; d=json.load(sys.stdin); "
            "print('source=', d.get('source')); "
            "print('count=', len(d.get('data') or [])); "
            "print('msg=', (d.get('message') or '')[:120])\""
        )
        run(client, verify_cmd)
        print(f"\nOpen: http://{HOST}:8000/create-product")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
