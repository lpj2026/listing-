#!/usr/bin/env python3
"""Configure nginx on port 80 to proxy /listing/ -> listing app on 8001."""
import os
import re
import sys

import paramiko

from deploy_config import LISTING_APP_PORT, REMOTE_DIR, REMOTE_HOST

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
AUTH_USER = os.environ.get("LISTING_AUTH_USER", "listing")
AUTH_PASSWORD = os.environ.get("LISTING_AUTH_PASSWORD", "")
CONF = "/etc/nginx/conf.d/ds.conf"
MARKER = "# product-listing (刊登系统)"
HTPASSWD = "/etc/nginx/.htpasswd_listing"


def build_snippet() -> str:
    auth_lines = ""
    if AUTH_PASSWORD:
        auth_lines = (
            "    auth_basic \"Listing System\";\n"
            f"    auth_basic_user_file {HTPASSWD};\n"
        )
    return f"""
  {MARKER} - 走 80 端口，无需开放 8001
  location /listing/ {{
    client_max_body_size 20m;
{auth_lines}    proxy_pass http://127.0.0.1:{LISTING_APP_PORT}/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 180s;
  }}
""".strip()


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


def upsert_listing_block(content: str, snippet: str) -> str:
    pattern = re.compile(
        rf"  {re.escape(MARKER)}.*?\n  location /listing/ \{{.*?\n  \}}\n",
        re.S,
    )
    if pattern.search(content):
        return pattern.sub(snippet + "\n\n", content, count=1)

    insert = snippet + "\n\n"
    if "  location / {" in content:
        return content.replace("  location / {", insert + "  location / {", 1)
    return content.rstrip() + "\n" + insert


def main():
    if not PASSWORD:
        print("Set REMOTE_SSH_PASSWORD")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(REMOTE_HOST, username="root", password=PASSWORD, timeout=20)
    try:
        if AUTH_PASSWORD:
            escaped = AUTH_PASSWORD.replace("'", "'\"'\"'")
            run(
                client,
                f"printf '%s:%s\\n' '{AUTH_USER}' \"$(openssl passwd -apr1 '{escaped}')\" > {HTPASSWD}",
            )
            run(client, f"chmod 644 {HTPASSWD}")
            print(f"HTTP Basic Auth enabled for user: {AUTH_USER}")
        else:
            print("LISTING_AUTH_PASSWORD not set, skipping HTTP Basic Auth")

        snippet = build_snippet()
        sftp = client.open_sftp()
        with sftp.file(CONF, "r") as f:
            content = f.read().decode("utf-8")
        content = upsert_listing_block(content, snippet)
        with sftp.file(CONF, "w") as f:
            f.write(content)
        sftp.close()
        print("updated", CONF)

        run(client, "nginx -t")
        run(client, "systemctl reload nginx || nginx -s reload")
        run(
            client,
            "curl -s -o /dev/null -w 'nginx_listing:%{http_code}\n' "
            "http://127.0.0.1/listing/create-product",
        )
        print(f"\n刊登系统: http://{REMOTE_HOST}/listing/create-product")
        if AUTH_PASSWORD:
            print(f"访问账号: {AUTH_USER}")
        print(f"补货系统继续用: http://{REMOTE_HOST}:8000/")
        print(f"服务目录: {REMOTE_DIR}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
