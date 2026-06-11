#!/usr/bin/env python3
"""Configure nginx on port 80 to proxy /listing/ -> listing app on 8001."""
import os
import sys

import paramiko

from deploy_config import LISTING_APP_PORT, REMOTE_HOST

PASSWORD = os.environ.get("REMOTE_SSH_PASSWORD", "")
NGINX_SNIPPET = """
  # product-listing (刊登系统) - 走 80 端口，无需开放 8001
  location /listing/ {
    client_max_body_size 20m;
    proxy_pass http://127.0.0.1:__PORT__/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 180s;
  }
""".replace("__PORT__", LISTING_APP_PORT)

CONF = "/etc/nginx/conf.d/ds.conf"
MARKER = "# product-listing (刊登系统)"


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

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(REMOTE_HOST, username="root", password=PASSWORD, timeout=20)
    try:
        sftp = client.open_sftp()
        with sftp.file(CONF, "r") as f:
            content = f.read().decode("utf-8")

        if MARKER in content:
            print("nginx listing proxy already configured")
        else:
            insert = NGINX_SNIPPET.strip() + "\n\n"
            if "  location / {" in content:
                content = content.replace("  location / {", insert + "  location / {", 1)
            else:
                content = content.rstrip() + "\n" + insert
            with sftp.file(CONF, "w") as f:
                f.write(content)
            print("updated", CONF)
        sftp.close()

        run(client, "nginx -t")
        run(client, "systemctl reload nginx || nginx -s reload")
        run(
            client,
            "curl -s -o /dev/null -w 'nginx_listing:%{http_code}\n' "
            "http://127.0.0.1/listing/create-product",
        )
        print(f"\n刊登系统（外网可访问）: http://{REMOTE_HOST}/listing/create-product")
        print(f"补货系统继续用: http://{REMOTE_HOST}:8000/")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
