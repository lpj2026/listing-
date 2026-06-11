#!/usr/bin/env bash
# 在阿里云服务器 8.137.177.25 上运行此脚本
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

if [ -z "${LINGXING_APP_ID:-}" ] || [ -z "${LINGXING_APP_SECRET:-}" ]; then
  echo "请先在 $ROOT/.env 中配置 LINGXING_APP_ID 和 LINGXING_APP_SECRET"
  exit 1
fi

echo "=== 当前服务器公网 IP ==="
curl -s https://api.ipify.org || curl -s ifconfig.me
echo ""

echo "=== 1. 测试 Token 获取 ==="
ENCODED_SECRET=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$LINGXING_APP_SECRET'))")
TOKEN_RESP=$(curl -s -X POST "https://openapi.lingxing.com/api/auth-server/oauth/access-token?appId=${LINGXING_APP_ID}&appSecret=${ENCODED_SECRET}")
echo "$TOKEN_RESP" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESP"

CODE=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('code',''))" 2>/dev/null || echo "fail")
if [ "$CODE" != "200" ]; then
  echo "[FAIL] Token 获取失败，请确认领星白名单已添加 8.137.177.25"
  exit 1
fi
echo "[OK] Token 获取成功"

echo ""
echo "=== 2. 启动 Web 服务 ==="
mkdir -p logs data
chmod +x scripts/server_start.sh

APP_PORT="${APP_PORT:-8000}"
for pid in $(netstat -tlnp 2>/dev/null | grep ":${APP_PORT} " | awk '{print $7}' | cut -d/ -f1); do
  kill -9 "$pid" 2>/dev/null || true
done

nohup bash scripts/server_start.sh > logs/app.log 2>&1 &
echo $! > app.pid
sleep 2

echo ""
echo "=== 3. 验证分类 API ==="
curl -s "http://127.0.0.1:${APP_PORT}/api/categories/root?store_id=12518" | python3 -m json.tool | head -n 30

echo ""
echo "[OK] 服务已启动"
echo "访问: http://8.137.177.25:${APP_PORT}/create-product"
echo "日志: tail -f $ROOT/logs/app.log"
