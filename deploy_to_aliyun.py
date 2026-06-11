#!/usr/bin/env python3
"""Deploy product listing system to Aliyun ECS."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("缺少 paramiko，请运行: pip install paramiko")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
REMOTE_HOST = os.environ.get("REMOTE_HOST", "8.137.177.25")
REMOTE_USER = os.environ.get("REMOTE_USER", "root")
REMOTE_PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
REMOTE_DIR = os.environ.get("REMOTE_DIR", "/opt/product-listing")
APP_PORT = os.environ.get("APP_PORT", "8001")

UPLOAD_ITEMS = [
    "backend",
    "frontend",
    "data",
    "scripts",
    "requirements.txt",
    ".env.example",
]

SKIP_DIR_NAMES = {"__pycache__", ".git", ".venv", "venv", "logs"}
SKIP_FILE_NAMES = {".gitignore", "deploy_to_aliyun.py", "deploy.bat"}


def log(msg: str) -> None:
    print(msg, flush=True)


def ssh_exec(client: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    log(f"$ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    return code, out, err


def collect_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for item in UPLOAD_ITEMS:
        path = ROOT / item
        if not path.exists():
            continue
        if path.is_file():
            files.append((path, item.replace("\\", "/")))
            continue
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(ROOT).as_posix()
            if any(part in SKIP_DIR_NAMES for part in file_path.parts):
                continue
            if file_path.name in SKIP_FILE_NAMES:
                continue
            files.append((file_path, rel))
    return files


def upload_project(sftp: paramiko.SFTPClient) -> None:
    files = collect_files()
    log(f"Uploading {len(files)} files to {REMOTE_DIR} ...")
    for local_path, remote_rel in files:
        remote_path = f"{REMOTE_DIR}/{remote_rel}".replace("\\", "/")
        remote_parent = os.path.dirname(remote_path)
        parts = remote_parent.split("/")
        current = ""
        for part in parts:
            if not part:
                continue
            current = f"{current}/{part}" if current else f"/{part}"
            try:
                sftp.stat(current)
            except OSError:
                sftp.mkdir(current)
        sftp.put(str(local_path), remote_path)


def build_remote_env() -> str:
    local_env = ROOT / ".env"
    lines = [
        "APP_HOST=0.0.0.0",
        f"APP_PORT={APP_PORT}",
        "DISABLE_REMOTE_PROXY=1",
        "LINGXING_DEFAULT_STORE_ID=12518",
        f"PUBLIC_HOST={REMOTE_HOST}",
        f"IMAGE_PUBLIC_BASE_URL=http://{REMOTE_HOST}/listing",
        "IMAGE_MAX_BYTES=10485760",
    ]
    present = {line.split("=", 1)[0] for line in lines if "=" in line}
    if local_env.exists():
        for raw in local_env.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key in {"APP_HOST", "APP_PORT"}:
                continue
            if key in present:
                lines = [item for item in lines if not item.startswith(f"{key}=")]
                present.discard(key)
            lines.append(line)
            present.add(key)
    else:
        lines.extend(
            [
                "LINGXING_APP_ID=",
                "LINGXING_APP_SECRET=",
            ]
        )
    return "\n".join(lines) + "\n"


def verify_remote(client: paramiko.SSHClient) -> None:
    log("\n=== Verify category API ===")
    cmd = (
        f"curl -s 'http://127.0.0.1:{APP_PORT}/api/categories/root?store_id=12518' | "
        "python3 -c \"import sys,json; d=json.load(sys.stdin); "
        "print('source=', d.get('source')); "
        "print('count=', len(d.get('data') or [])); "
        "print('message=', d.get('message','')[:120])\""
    )
    ssh_exec(client, cmd)


def main() -> int:
    if not REMOTE_PASSWORD:
        log("请设置环境变量 REMOTE_SSH_PASSWORD 后再运行部署脚本。")
        log("PowerShell 示例:")
        log("  $env:REMOTE_SSH_PASSWORD='你的服务器root密码'")
        log("  python deploy_to_aliyun.py")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    log(f"Connecting to {REMOTE_USER}@{REMOTE_HOST} ...")
    client.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASSWORD, timeout=20)

    try:
        ssh_exec(client, f"mkdir -p {REMOTE_DIR}/logs {REMOTE_DIR}/data")
        sftp = client.open_sftp()
        try:
            upload_project(sftp)
            with sftp.file(f"{REMOTE_DIR}/.env", "w") as remote_env:
                remote_env.write(build_remote_env())
        finally:
            sftp.close()

        ssh_exec(client, f"sed -i 's/\\r$//' {REMOTE_DIR}/scripts/server_start.sh")
        ssh_exec(client, f"chmod +x {REMOTE_DIR}/scripts/server_start.sh")
        ssh_exec(
            client,
            f"cd {REMOTE_DIR} && pip3 install -q -r requirements.txt || python3 -m pip install -q -r requirements.txt",
        )

        stop_cmd = (
            f"for pid in $(netstat -tlnp 2>/dev/null | grep ':{APP_PORT} ' | awk '{{print $7}}' | cut -d/ -f1); do "
            f"kill -9 $pid 2>/dev/null || true; done; "
            f"pkill -f '{REMOTE_DIR}/backend/app.py' 2>/dev/null || true"
        )
        ssh_exec(client, stop_cmd)

        start_cmd = (
            f"cd {REMOTE_DIR} && nohup bash scripts/server_start.sh > logs/app.log 2>&1 & "
            f"echo $! > app.pid && sleep 2 && cat app.pid"
        )
        code, out, _ = ssh_exec(client, start_cmd)
        if code != 0:
            log("启动失败，查看 logs/app.log")
            ssh_exec(client, f"tail -n 40 {REMOTE_DIR}/logs/app.log")
            return 1

        time.sleep(2)
        verify_remote(client)

        log("\n=== Verify image upload API ===")
        ssh_exec(
            client,
            f"curl -s -o /dev/null -w 'image_upload:%{{http_code}}\n' "
            f"-F 'file=@/etc/hosts;filename=test.jpg;type=image/jpeg' "
            f"http://127.0.0.1:{APP_PORT}/api/images/upload",
        )

        log("\n=== Deploy success ===")
        log(f"Open: http://{REMOTE_HOST}/listing/create-product")
        log(f"Direct: http://{REMOTE_HOST}:{APP_PORT}/create-product")
        log(f"若浏览器打不开，请在阿里云安全组放行 TCP {APP_PORT}")
        log(f"Logs: ssh {REMOTE_USER}@{REMOTE_HOST} 'tail -f {REMOTE_DIR}/logs/app.log'")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
