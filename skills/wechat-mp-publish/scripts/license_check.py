#!/usr/bin/env python3
"""license 校验与功能门槛（买家侧）。

用法：
  python3 license_check.py            # 开工门：显示授权状态。退出码 0=可开工 1=license 无效
  python3 license_check.py --paid     # 付费功能门（封面裁剪/发表前置四项/发表确认链前必跑）。
                                      # 退出码 0=已授权 3=试用版无此功能（向用户展示二维码）

无 license.key 即为免费试用版：可永久使用「建草稿到草稿箱」，付费功能走 --paid 门槛。
license.key 由卖家随交付发放，放本技能目录即可。
"""
import base64, datetime, json, pathlib, sys
from cryptography.hazmat.primitives.serialization import load_pem_public_key

PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAjDwNwwozgf++9VLXEFwds6T7y5y73uVyZy0mliBc3gQ=
-----END PUBLIC KEY-----"""

HERE = pathlib.Path(__file__).resolve().parent
QR = HERE / "assets" / "join-wechat.png"


def b64dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def load_license():
    """返回 (payload, None) 或 (None, 错误信息)。license 不存在返回 (None, None) 表示试用版。"""
    path = HERE / "license.key"
    if not path.exists():
        return None, None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        raw = b64dec(doc["payload"])
        payload = json.loads(raw)
        load_pem_public_key(PUBLIC_KEY_PEM).verify(b64dec(doc["sig"]), raw)
        if payload.get("product") != "mp-publish-pro":
            return None, "license 与本产品不匹配。"
        return payload, None
    except Exception:
        return None, "license 无效（签名不符或文件损坏）。请找卖家核对发放的文件是否完整，或删除 license.key 以试用版继续。"


def paid_gate_msg():
    lines = ["【试用版提示】封面裁剪、发表前置四项（原创声明/赞赏/合集/创作来源）、发表确认链为付费版功能。",
             "免费版止步「保存为草稿」——草稿已就绪，人工点开公众号后台即可完成剩余步骤。",
             "升级正式版（买断 + 年费更新）：扫码加微信，备注「公众号技能」。"]
    if QR.exists():
        lines += [f"二维码图片：{QR}",
                  f"请执行 `open '{QR}'` 向用户展示二维码后停下等用户操作。"]
    else:
        lines += ["（本副本未嵌入二维码，请联系卖家获取购买方式。）"]
    return "\n".join(lines)


def main() -> int:
    payload, err = load_license()
    if err:
        print(err)
        return 1

    if "--paid" in sys.argv:
        if payload is None:
            print(paid_gate_msg())
            return 3
        expired = datetime.date.today().isoformat() > payload.get("update_until", "")
        if expired:
            print(f"license 更新期已过（{payload['update_until']}）。已交付版本的功能可继续用，"
                  f"但此付费功能需有效更新期。续费后找卖家换新 license。")
            return 2
        print(f"已授权：{payload['buyer']}（GitHub: {payload['github']}）")
        return 0

    # 开工门（默认）
    if payload is None:
        print("试用版已就绪：可使用「建草稿/正文/配图/存草稿」全流程；"
              "封面裁剪与发表相关为付费功能（届时会再提示）。")
        return 0
    expired = datetime.date.today().isoformat() > payload.get("update_until", "")
    state = f"已授权：{payload['buyer']}（GitHub: {payload['github']}），更新期至 {payload['update_until']}"
    print(state + ("\n更新期已过：当前版本可继续使用，拿不到更新与答疑。续费后找卖家换新 license。" if expired else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
