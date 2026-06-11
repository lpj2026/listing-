"""店铺账号与站点配置，后续对接领星 API 时按 full_name 匹配 sid。"""

from __future__ import annotations

SITE_META = {
    "CA": {"site_name": "加拿大", "marketplace_id": "A2EUQ1WTGCTBG2"},
    "MX": {"site_name": "墨西哥", "marketplace_id": "A1AM78C64UM0Y8"},
    "US": {"site_name": "美国", "marketplace_id": "ATVPDKIKX0DER"},
}

# (店铺账号全名, 站点中文名)
STORE_ENTRIES = [
    ("US1-刘子洋-CA", "加拿大"),
    ("US1-刘子洋-MX", "墨西哥"),
    ("US1-刘子洋-US", "美国"),
    ("US1-勇成励-CA", "加拿大"),
    ("US1-勇成励-MX", "墨西哥"),
    ("US1-勇成励-US", "美国"),
    ("US1-川服喜-CA", "加拿大"),
    ("US1-川服喜-MX", "墨西哥"),
    ("US1-川服喜-US", "美国"),
    ("US1-恒游千-CA", "加拿大"),
    ("US1-恒游千-MX", "墨西哥"),
    ("US1-恒游千-US", "美国"),
    ("US1-智链通-CA", "加拿大"),
    ("US1-智链通-MX", "墨西哥"),
    ("US1-智链通-US", "美国"),
    ("US1-水金余-CA", "加拿大"),
    ("US1-水金余-MX", "墨西哥"),
    ("US1-水金余-US", "美国"),
    ("US1-穆厚-CA", "加拿大"),
    ("US1-穆厚-MX", "墨西哥"),
    ("US1-穆厚-US", "美国"),
    ("US1-茂林怡然-CA", "加拿大"),
    ("US1-茂林怡然-MX", "墨西哥"),
    ("US1-茂林怡然-US", "美国"),
    ("US1-重庆茁凯-CA", "加拿大"),
    ("US1-重庆茁凯-MX", "墨西哥"),
    ("US1-重庆茁凯-US", "美国"),
    ("US1-鼎晟华-CA", "加拿大"),
    ("US1-鼎晟华-MX", "墨西哥"),
    ("US1-鼎晟华-US", "美国"),
    ("US2-奥诺兰-CA", "加拿大"),
    ("US2-奥诺兰-US", "美国"),
    ("US2-峻跃昆昇-CA", "加拿大"),
    ("US2-峻跃昆昇-US", "美国"),
    ("US2-斯鑫雅-CA", "加拿大"),
    ("US2-斯鑫雅-US", "美国"),
    ("US2-旌越问-CA", "加拿大"),
    ("US2-旌越问-US", "美国"),
    ("US2-韵盛余-CA", "加拿大"),
    ("US2-韵盛余-US", "美国"),
    ("US3-优贝诺-CA", "加拿大"),
    ("US3-优贝诺-MX", "墨西哥"),
    ("US3-优贝诺-US", "美国"),
    ("US3-吉西瑞雅-CA", "加拿大"),
    ("US3-吉西瑞雅-MX", "墨西哥"),
    ("US3-吉西瑞雅-US", "美国"),
    ("US3-富琳顿-CA", "加拿大"),
    ("US3-富琳顿-MX", "墨西哥"),
    ("US3-富琳顿-US", "美国"),
    ("US3-新志楠-CA", "加拿大"),
    ("US3-新志楠-MX", "墨西哥"),
    ("US3-新志楠-US", "美国"),
    ("US3-智鑫弘-CA", "加拿大"),
    ("US3-智鑫弘-MX", "墨西哥"),
    ("US3-智鑫弘-US", "美国"),
    ("US3-睿启君--CA", "加拿大"),
    ("US3-睿启君--MX", "墨西哥"),
    ("US3-睿启君-US", "美国"),
    ("US3-胡思妍-CA", "加拿大"),
    ("US3-胡思妍-MX", "墨西哥"),
    ("US3-胡思妍-US", "美国"),
]

SITE_NAME_TO_CODE = {meta["site_name"]: code for code, meta in SITE_META.items()}


def parse_account(full_name: str) -> tuple[str, str]:
    for code in ("CA", "MX", "US"):
        suffix = f"-{code}"
        if full_name.endswith(suffix):
            return full_name[: -len(suffix)], code
        double_suffix = f"--{code}"
        if full_name.endswith(double_suffix):
            return full_name[: -len(double_suffix)], code
    raise ValueError(f"无法解析店铺账号：{full_name}")


def build_stores() -> list[dict]:
    stores = []
    for index, (full_name, site_name) in enumerate(STORE_ENTRIES, start=1):
        account, site_code = parse_account(full_name)
        if SITE_META[site_code]["site_name"] != site_name:
            raise ValueError(f"店铺与站点不匹配：{full_name} / {site_name}")
        stores.append(
            {
                "id": index,
                "account": account,
                "full_name": full_name,
                "site_code": site_code,
                "site_name": site_name,
                "marketplace_id": SITE_META[site_code]["marketplace_id"],
            }
        )
    return stores
