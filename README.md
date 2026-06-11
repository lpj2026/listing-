# 领星刊登系统

当前版本先实现店小秘风格的 Amazon 创建产品模板，使用本地 Mock 数据跑通页面结构与草稿保存流程。后续按系统需求逐步替换为领星开放 API。

## 本地启动（日常开发）

本项目**默认本地运行**即可，Mock 数据可完整跑通页面、草稿、刊登任务流程。

双击运行：

```text
start.bat
```

或命令行：

```powershell
cd backend
python app.py
```

默认端口 **8001**（与补货系统 8000 分开，互不干扰）。

浏览器打开：

```text
http://127.0.0.1:8001/create-product
http://127.0.0.1:8001/create_product
```

## 当前包含

- 创建产品页面
- 基本信息、店小秘信息、产品信息、产品属性、价格信息、产品图片、描述信息、运输信息、关键词信息
- 右侧分区导航
- Mock 店铺、分类、Schema 属性
- 领星分类树对接（`categoryRoot` / `categoryChildren`）+ 四列级联选择器
- 表单数据转换为亚马逊 `attributes` 结构的预览逻辑
- 草稿保存、草稿列表、草稿恢复
- 本地刊登任务生成、任务列表

## 本地数据

开发期数据保存到：

```text
data/drafts.json
data/tasks.json
```

这两份文件只是本地开发数据，后续会替换为数据库表。

## 对接领星真实数据（需服务器公网 IP）

本地开发用 Mock 数据即可。**只有对接领星真实分类 / 店铺 / 刊登 API 时**，才需要把服务部署到已在领星 IP 白名单的服务器（`8.137.177.25`）。

| 场景 | 方式 |
|------|------|
| 页面开发、草稿、Mock 流程 | 本地 `start.bat`，端口 8001 |
| 领星真实分类、发布等 API | 部署到阿里云，走白名单 IP |

服务器访问地址（与补货系统分开）：

| 项目 | 访问地址 |
|------|----------|
| 补货系统 | `http://8.137.177.25:8000/` |
| **刊登系统（本项目）** | `http://8.137.177.25/listing/create-product` |

<details>
<summary>阿里云一键部署（仅对接领星时需要）</summary>

1. 确认 `d:\Product\.env` 已配置领星凭证
2. 在 PowerShell 中执行：

```powershell
cd d:\Product
$env:REMOTE_SSH_PASSWORD="你的阿里云root密码"
python deploy_to_aliyun.py
```

或直接双击 `deploy.bat`（需先 `set REMOTE_SSH_PASSWORD=...`）

3. 部署成功后访问：`http://8.137.177.25/listing/create-product`

服务器上手动启动：

```bash
cd /opt/product-listing
bash run_on_aliyun.sh
tail -f /opt/product-listing/logs/app.log
```

</details>

## 分类选择器

1. 先选择店铺账号和站点
2. 点击「选择分类」打开四列级联弹窗
3. 逐级点选到末级分类，点击「确定」

数据来源：

- **本地开发**：默认 Mock 分类数据，无需配置领星凭证
- **对接真实 API**：在 `.env` 配置 `LINGXING_APP_ID` / `LINGXING_APP_SECRET`，并在白名单 IP 上运行（本地 IP 未加白名单时会 403，自动回退 Mock）

## 下一步（领星 Listing 对接）

| 阶段 | 状态 | 内容 |
|------|------|------|
| 阶段一 | ✅ 部分完成 | 鉴权、店铺列表 API、本地启动 |
| 阶段二 | 🔄 进行中 | 分类树 ✅、Schema 动态加载 ✅、草稿 ✅ |
| 阶段三 | ✅ 基本完成 | publish 提交 ✅、结果自动轮询 ✅（30s 起，最长 15 分钟） |
| 阶段四 | ✅ 基本完成 | Listing 同步检测 ✅、SKU 自动配对 ✅（需填本地 SKU） |
| 阶段五 | ⏳ 待做 | 变体、批量刊登、更新已有商品、OSS 图片 |

本地 Mock 可继续开发 UI；**真实刊登测试**需在阿里云白名单 IP 上用测试 MSKU 验证。
