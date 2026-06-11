#!/usr/bin/env python3
"""
领星 ERP 开放平台可行性测试脚本

用途：验证「自研刊登系统 → 领星 → 亚马逊」这条链路中，
      领星开放 API 实际能覆盖哪些能力。

运行前准备：
1. 领星后台：设置 > 业务配置 > 全局 > 开放接口
2. 将本机公网 IP 加入白名单
3. 复制 AppID、AppSecret
4. 设置环境变量：
   set LINGXING_APP_ID=你的AppID
   set LINGXING_APP_SECRET=你的AppSecret

运行：
   python lingxing_feasibility_test.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

try:
    import requests
    from Crypto.Cipher import AES
except ImportError:
    print("缺少依赖，请先运行: pip install requests pycryptodome")
    sys.exit(1)


BASE_URL = "https://openapi.lingxing.com"
AUTH_URL = f"{BASE_URL}/api/auth-server/oauth/access-token"

# 根据领星开源 SDK 整理的已知 API 端点
KNOWN_ENDPOINTS = {
    "auth": {
        "name": "获取 Access Token",
        "method": "POST",
        "path": "/api/auth-server/oauth/access-token",
        "category": "授权",
        "supports_listing_publish": False,
    },
    "seller_lists": {
        "name": "查询亚马逊店铺列表",
        "method": "GET",
        "path": "/erp/sc/data/seller/lists",
        "category": "基础数据",
        "supports_listing_publish": False,
    },
    "listing_query": {
        "name": "查询 Listing（亚马逊已上架商品）",
        "method": "POST",
        "path": "/erp/sc/data/mws/listing",
        "category": "销售-Listing",
        "supports_listing_publish": False,
        "note": "只读，数据来自亚马逊 All Listing 报表同步",
    },
    "listing_pair": {
        "name": "MSKU 与本地 SKU 配对",
        "method": "POST",
        "path": "/erp/sc/storage/product/link",
        "category": "销售-Listing",
        "supports_listing_publish": False,
        "note": "仅配对，不能创建新 Listing",
    },
    "local_product_list": {
        "name": "查询本地产品列表",
        "method": "POST",
        "path": "/erp/sc/routing/data/local_inventory/productList",
        "category": "产品",
        "supports_listing_publish": False,
    },
    "local_product_set": {
        "name": "添加/编辑本地产品",
        "method": "POST",
        "path": "/erp/sc/routing/storage/product/set",
        "category": "产品",
        "supports_listing_publish": False,
        "note": "创建的是领星本地 SKU，不是亚马逊 Listing",
    },
    # 以下端点在公开 SDK/文档中未找到，刊登需走领星 UI
    "listing_draft_create": {
        "name": "创建刊登草稿",
        "method": "POST",
        "path": "/erp/sc/???/publication/draft",
        "category": "刊登管理",
        "supports_listing_publish": True,
        "note": "公开 API 未提供，仅在领星 UI「刊登管理>草稿箱」可用",
        "available": False,
    },
    "listing_publish": {
        "name": "发布刊登草稿到亚马逊",
        "method": "POST",
        "path": "/erp/sc/???/publication/publish",
        "category": "刊登管理",
        "supports_listing_publish": True,
        "note": "公开 API 未提供，走刊登队列提交到亚马逊 SP-API",
        "available": False,
    },
    "listing_upload_file": {
        "name": "上传新版表格批量刊登",
        "method": "POST",
        "path": "/erp/sc/???/listing/upload",
        "category": "刊登管理",
        "supports_listing_publish": True,
        "note": "公开 API 未提供，仅在领星 UI「Listing>导入>上传商品」可用",
        "available": False,
    },
}


@dataclass
class TestResult:
    name: str
    success: bool
    message: str
    data: Any = None


class LingxingClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token: str | None = None

    def _aes_ecb_encrypt(self, text: str) -> str:
        key = self.app_id.encode("utf-8")
        cipher = AES.new(key, AES.MODE_ECB)
        data = text.encode("utf-8")
        pad_len = 16 - len(data) % 16
        data += bytes([pad_len]) * pad_len
        encrypted = cipher.encrypt(data)
        return base64.b64encode(encrypted).decode("utf-8")

    def _sign(self, params: dict[str, Any]) -> str:
        items = []
        for key in sorted(params.keys()):
            value = params[key]
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            else:
                value_str = str(value)
            items.append(f"{key}={value_str}")
        raw = "&".join(items)
        md5_value = hashlib.md5(raw.encode("utf-8")).hexdigest().upper()
        return self._aes_ecb_encrypt(md5_value)

    def get_token(self) -> str:
        url = (
            f"{AUTH_URL}?appId={self.app_id}"
            f"&appSecret={urllib.parse.quote(self.app_secret)}"
        )
        resp = requests.post(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        if str(payload.get("code")) != "200":
            raise RuntimeError(f"获取 Token 失败: {payload}")
        self.access_token = payload["data"]["access_token"]
        return self.access_token

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.access_token:
            self.get_token()

        timestamp = str(int(time.time()))
        query_params: dict[str, Any] = {
            "app_key": self.app_id,
            "access_token": self.access_token,
            "timestamp": timestamp,
        }
        sign_params = dict(query_params)
        if body:
            sign_params.update(body)

        sign = self._sign(sign_params)
        query_params["sign"] = sign

        url = f"{BASE_URL}{path}"
        if method.upper() == "GET":
            resp = requests.get(url, params=query_params, timeout=30)
        else:
            resp = requests.post(url, params=query_params, json=body or {}, timeout=30)

        try:
            return resp.json()
        except Exception:
            return {"http_status": resp.status_code, "text": resp.text[:500]}


def print_section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def test_api_surface() -> list[TestResult]:
    """静态分析：公开 API 是否支持刊登发布"""
    results = []
    publish_apis = [k for k, v in KNOWN_ENDPOINTS.items() if v.get("supports_listing_publish")]
    available_publish = [k for k in publish_apis if KNOWN_ENDPOINTS[k].get("available", True)]

    results.append(
        TestResult(
            name="刊登相关公开 API 检查",
            success=len(available_publish) == 0,
            message=(
                f"刊登发布类 API 可用数: {len(available_publish)}/{len(publish_apis)}。"
                "公开 SDK 仅提供 Listing 查询和配对，不提供草稿创建/发布接口。"
            ),
        )
    )
    return results


def test_live_connection(client: LingxingClient) -> list[TestResult]:
    results: list[TestResult] = []

    # 1. Token
    try:
        token = client.get_token()
        results.append(
            TestResult(
                name="API 授权连通性",
                success=True,
                message=f"Token 获取成功（前8位: {token[:8]}...）",
            )
        )
    except Exception as exc:
        results.append(
            TestResult(
                name="API 授权连通性",
                success=False,
                message=str(exc),
            )
        )
        return results

    # 2. 店铺列表
    try:
        data = client.request("GET", "/erp/sc/data/seller/lists")
        code = data.get("code", data.get("code"))
        if code == 0 or str(code) == "0":
            sellers = data.get("data", [])
            results.append(
                TestResult(
                    name="查询亚马逊店铺",
                    success=True,
                    message=f"成功，共 {len(sellers)} 个店铺",
                    data=[{"sid": s.get("sid"), "name": s.get("name"), "country": s.get("country")} for s in sellers[:5]],
                )
            )
            first_sid = sellers[0]["sid"] if sellers else None
        else:
            results.append(TestResult("查询亚马逊店铺", False, f"返回: {data}"))
            first_sid = None
    except Exception as exc:
        results.append(TestResult("查询亚马逊店铺", False, str(exc)))
        first_sid = None

    # 3. Listing 查询（只读）
    if first_sid:
        try:
            data = client.request(
                "POST",
                "/erp/sc/data/mws/listing",
                {"sid": first_sid, "is_pair": 2, "offset": 0, "length": 5},
            )
            code = data.get("code")
            if code == 0 or str(code) == "0":
                listings = data.get("data", [])
                results.append(
                    TestResult(
                        name="查询 Listing（只读）",
                        success=True,
                        message=f"成功，返回 {len(listings)} 条（未配对商品样本）",
                        data=[
                            {
                                "msku": item.get("seller_sku"),
                                "asin": item.get("asin"),
                                "title": (item.get("item_name") or "")[:40],
                            }
                            for item in listings[:3]
                        ],
                    )
                )
            else:
                results.append(TestResult("查询 Listing（只读）", False, f"返回: {data}"))
        except Exception as exc:
            results.append(TestResult("查询 Listing（只读）", False, str(exc)))

    # 4. 本地产品列表
    try:
        data = client.request(
            "POST",
            "/erp/sc/routing/data/local_inventory/productList",
            {"offset": 0, "length": 5},
        )
        code = data.get("code")
        if code == 0 or str(code) == "0":
            products = data.get("data", [])
            results.append(
                TestResult(
                    name="查询本地产品",
                    success=True,
                    message=f"成功，返回 {len(products)} 条",
                    data=[{"sku": p.get("sku"), "name": p.get("product_name")} for p in products[:3]],
                )
            )
        else:
            results.append(TestResult("查询本地产品", False, f"返回: {data}"))
    except Exception as exc:
        results.append(TestResult("查询本地产品", False, str(exc)))

    return results


def print_feasibility_conclusion() -> None:
    print_section("可行性结论")

    print(
        """
【你的想法】
  自研系统（类似店小秘）→ 上传到领星 Listing → 亚马逊库存自动同步

【关键纠正】
  领星「Listing」页面 ≠ 刊登入口，它是亚马逊数据的「只读镜像」。
  数据来源：亚马逊 All Listing 报表 -> 领星同步（约15分钟~1小时）
  因此不能把新产品「直接写到 Listing」，Listing 是结果，不是输入。

【店小秘实际在做什么】
  填写刊登表单 -> 调用亚马逊 SP-API（putListingsItem）-> 创建 Listing
  -> 亚马逊后台出现商品 -> 领星/店小秘再同步回来

【领星开放 API 实测能力（基于公开 SDK）】
  [OK] 可用：查询店铺、查询 Listing、MSKU配对、查询/创建本地产品
  [NO] 不可用：创建刊登草稿、发布到亚马逊、上传刊登表格

【推荐实现路径（按可行性排序）】

  方案 A【推荐】自研刊登 UI + 直连亚马逊 SP-API
    - 你的系统负责表单、校验、图片、类目属性
    - 直接调用 Amazon putListingsItem 发布
    - 领星会自动从亚马逊同步到 Listing（无需写领星 Listing）
    - 发布后用领星 API 做 MSKU 与本地 SKU 配对

  方案 B【过渡】自研 UI + 生成亚马逊新版表格 + 领星 UI 上传
    - 员工在自研系统填表，导出亚马逊「新模板测试版」表格
    - 人工/自动化上传到领星「Listing > 导入 > 上传商品」
    - 适合短期验证，长期仍需自动化

  方案 C【需商务】联系领星开通刊登类企业 API
    - 领星自研集成方案页面提到 API 对接能力
    - 刊登草稿/发布接口可能仅对企业客户开放
    - 建议向领星客服确认是否有「刊登管理」开放接口

  方案 D【不推荐】浏览器自动化操作领星刊登页面
    - 可做 POC，但维护成本高、易因页面改版失效

【数据流示意】

  当前（店小秘）:
    员工 -> 店小秘刊登表单 -> 亚马逊 SP-API -> Seller Central 库存
                                    |
                              领星 Listing 同步

  目标（自研）:
    员工 -> 自研刊登系统 -> 亚马逊 SP-API -> Seller Central 库存
                              |
                        领星 Listing 自动同步
                              |
                        领星 API 做 SKU 配对
"""
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print_section("领星 ERP 刊登链路可行性测试")

    app_id = os.environ.get("LINGXING_APP_ID", "").strip()
    app_secret = os.environ.get("LINGXING_APP_SECRET", "").strip()

    # 静态 API 面分析（无需凭证）
    static_results = test_api_surface()
    print_section("1. 公开 API 能力分析（静态）")
    for r in static_results:
        status = "[OK]" if r.success else "[FAIL]"
        print(f"  {status} {r.name}: {r.message}")

    print("\n  已知端点清单:")
    for key, ep in KNOWN_ENDPOINTS.items():
        available = ep.get("available", True)
        flag = "[OK]" if available else "[NO]"
        print(f"    {flag} [{ep['category']}] {ep['name']}")
        if ep.get("note"):
            print(f"       说明: {ep['note']}")

    # 动态连通性测试（需要凭证）
    print_section("2. 领星 API 连通性测试（动态）")
    if not app_id or not app_secret:
        print(
            "  [WARN] 未配置 LINGXING_APP_ID / LINGXING_APP_SECRET，跳过在线测试。\n"
            "  配置方法（PowerShell）:\n"
            "    $env:LINGXING_APP_ID='你的AppID'\n"
            "    $env:LINGXING_APP_SECRET='你的AppSecret'\n"
            "    python lingxing_feasibility_test.py"
        )
    else:
        client = LingxingClient(app_id, app_secret)
        live_results = test_live_connection(client)
        for r in live_results:
            status = "[OK]" if r.success else "[FAIL]"
            print(f"  {status} {r.name}: {r.message}")
            if r.data:
                print(f"       样本: {json.dumps(r.data, ensure_ascii=False)}")

    print_feasibility_conclusion()


if __name__ == "__main__":
    main()
