#!/usr/bin/env python3
import os
import sys
import time

import paramiko

REMOTE = "/opt/product-listing"
IMG = "20260610/2fdc44b9443c49359b71b05056efe937.png"


def run(client, cmd, timeout=30):
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
    password = os.environ.get("REMOTE_SSH_PASSWORD", "")
    if not password:
        print("Set REMOTE_SSH_PASSWORD")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("8.137.177.25", username="root", password=password, timeout=20)
    try:
        run(client, f"ls -la {REMOTE}/data/uploads/{IMG} || true")
        run(client, f"curl -s -o /dev/null -w 'direct8001:%{{http_code}}\n' http://127.0.0.1:8001/uploads/{IMG}")
        run(client, f"curl -s -o /dev/null -w 'nginx:%{{http_code}}\n' http://127.0.0.1/listing/uploads/{IMG}")
        run(client, f"netstat -tlnp | grep 8001 || true")
        run(client, f"tail -n 15 {REMOTE}/logs/app.log || true")
        for cmd in [
            f"sed -i 's/\\r$//' {REMOTE}/scripts/server_start.sh",
            f"pkill -f '{REMOTE}/backend/app.py' || true",
            f"cd {REMOTE} && setsid bash scripts/server_start.sh > logs/app.log 2>&1 &",
        ]:
            client.exec_command(cmd, timeout=15)
        time.sleep(4)
        run(client, f"curl -s -o /dev/null -w 'after:%{{http_code}}\n' http://127.0.0.1/listing/uploads/{IMG}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
