#!/usr/bin/env python3
import os
import sys
import time
import paramiko

HOST = "8.137.177.25"
PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
REMOTE = "/opt/product-listing"
PY = "python3.8"


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
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=PASSWORD, timeout=20)
    try:
        run(client, "fuser -k 8000/tcp 2>/dev/null || true")
        run(client, "pkill -9 -f '/opt/product-listing/backend/app.py' || true")
        client.exec_command(
            f"cd {REMOTE} && setsid bash scripts/server_start.sh >> logs/app.log 2>&1 < /dev/null &"
        )
        time.sleep(4)
        run(client, f"tail -n 8 {REMOTE}/logs/app.log")
        run(client, "netstat -tlnp | grep 8000 || true")
        run(
            client,
            f"curl -s http://127.0.0.1:8000/api/categories/root?store_id=12518 | {PY} -c \"import sys,json;d=json.load(sys.stdin);print('source=',d.get('source'));print('count=',len(d.get('data') or []));print('first=', (d.get('data') or [{{}}])[0].get('name',''))\"",
        )
        run(
            client,
            f"curl -s 'http://127.0.0.1:8000/api/categories/children?store_id=12518&parent_id=107883919482814472' | {PY} -c \"import sys,json;d=json.load(sys.stdin);print('source=',d.get('source'));print('count=',len(d.get('data') or []));print('first=', (d.get('data') or [{{}}])[0].get('name',''))\"",
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
