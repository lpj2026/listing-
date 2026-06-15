#!/usr/bin/env bash
# 在阿里云服务器上手动重启刊登服务
# 用法: bash run_on_aliyun.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

APP_PORT="${APP_PORT:-8001}"
export DISABLE_REMOTE_PROXY="${DISABLE_REMOTE_PROXY:-1}"

mkdir -p logs data data/uploads
sed -i 's/\r$//' scripts/server_start.sh 2>/dev/null || true
chmod +x scripts/server_start.sh

for pid in $(netstat -tlnp 2>/dev/null | grep ":${APP_PORT} " | awk '{print $7}' | cut -d/ -f1); do
  kill -9 "$pid" 2>/dev/null || true
done
pkill -f "${ROOT}/backend/app.py" 2>/dev/null || true

setsid bash scripts/server_start.sh >> logs/app.log 2>&1 < /dev/null &
sleep 3

HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${APP_PORT}/create-product")
if [ "$HTTP_CODE" != "200" ]; then
  echo "[FAIL] 服务未启动，HTTP $HTTP_CODE"
  tail -n 30 logs/app.log
  exit 1
fi

echo "[OK] 刊登系统已启动"
echo "访问: http://$(curl -s ifconfig.me 2>/dev/null || echo 127.0.0.1)/listing/create-product"
echo "日志: tail -f $ROOT/logs/app.log"
