# 领星刊登系统

Amazon 创建产品 / 刊登工具（店小秘风格 UI + 领星 Schema 动态属性）。

## 项目结构

```
backend/          # Python API（领星对接、Schema、刊登、图片）
frontend/         # 静态页面（index.html + app.js + styles.css）
data/             # 本地数据（草稿、任务、上传图片）
scripts/          # 服务器启动脚本
deploy_to_aliyun.py   # 一键部署到阿里云
deploy_config.py      # 部署配置（主机、目录、端口）
start.bat             # 本地启动
```

## 本地开发

```powershell
# 安装依赖
pip install -r requirements.txt

# 复制并编辑环境变量
copy .env.example .env

# 启动（端口 8001）
start.bat
```

浏览器打开：http://127.0.0.1:8001/create-product

未配置领星凭证时使用 Mock 数据，可完整调试页面与草稿流程。

## 公司内部使用（推荐）

同事直接访问线上环境，不要用 `127.0.0.1`：

**http://8.137.177.25/listing/create-product**

## 部署到阿里云

```powershell
$env:REMOTE_SSH_PASSWORD="服务器root密码"
python deploy_to_aliyun.py

# 可选：配置 nginx 访问密码（推荐）
$env:LISTING_AUTH_USER="listing"
$env:LISTING_AUTH_PASSWORD="你的访问密码"
python setup_nginx_listing.py
```

部署脚本**不会**覆盖服务器上的 `data/drafts.json` 和 `data/tasks.json`。

服务器上手动重启：

```bash
cd /opt/product-listing
bash run_on_aliyun.sh
```

## 环境变量（.env）

| 变量 | 说明 |
|------|------|
| `LINGXING_APP_ID` | 领星开放平台 AppID |
| `LINGXING_APP_SECRET` | 领星 AppSecret |
| `PUBLIC_HOST` | 公网 IP 或域名 |
| `IMAGE_PUBLIC_BASE_URL` | 图片公网前缀，如 `http://IP/listing` |
| `DISABLE_REMOTE_PROXY` | 线上设为 `1` |
| `ALLOW_HTTP_IMAGES` | 未配置 OSS 时临时允许 HTTP 图片（生产建议配 OSS 后关闭） |
| `LISTING_AUTH_USER` / `LISTING_AUTH_PASSWORD` | nginx 访问密码（见 `setup_nginx_listing.py`） |

领星 API 要求服务器公网 IP 在白名单内。

## 文档

- [首次真实刊登测试指南](docs/首次真实刊登测试指南.md)
- [开发流程说明](docs/领星刊登系统开发流程.md)
