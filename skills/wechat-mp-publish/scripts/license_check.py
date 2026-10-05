#!/usr/bin/env python3
"""license 校验（买家侧）。退出码：0=有效 1=无效/被篡改 2=签名真但更新期已过。

发布前必须通过：python3 license_check.py [license文件路径]
license 文件默认在技能目录的 license.key，由卖家随交付私信发放。
"""
import base64, datetime, json, pathlib, sys
from cryptography.hazmat.primitives.serialization import load_pem_public_key

PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAjDwNwwozgf++9VLXEFwds6T7y5y73uVyZy0mliBc3gQ=
-----END PUBLIC KEY-----"""

HERE = pathlib.Path(__file__).resolve().parent


def b64dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "license.key"
    if not path.exists():
        print(f"未找到 license：{path}\n请把卖家发放的 license.key 放到 {HERE}/ 下再发布。")
        return 1
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        raw = b64dec(doc["payload"])
        payload = json.loads(raw)
        load_pem_public_key(PUBLIC_KEY_PEM).verify(b64dec(doc["sig"]), raw)
    except Exception:
        print("license 无效（签名不符或文件损坏）。请找卖家核对发放的文件是否完整。")
        return 1
    if payload.get("product") != "mp-publish-pro":
        print("license 与本产品不匹配。")
        return 1
    expired = datetime.date.today().isoformat() > payload.get("update_until", "")
    state = f"已授权：{payload['buyer']}（GitHub: {payload['github']}），更新期至 {payload['update_until']}"
    if expired:
        print(state + "\n更新期已过：当前版本可继续使用，但拿不到更新与答疑。续费后找卖家换新 license。")
        return 2
    print(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
