#!/usr/bin/env python3
"""mp_upload.py — 通过公众号 filetransfer 接口把图片上传到素材库（无需 UI）

前置：mp_draft.py 已建草稿（编辑器页面打开着，票据从页面 JS 取）。
票据：window.wx.commonData.data 的 uin / ticket / t(token)。

用法:
    python3 mp_upload.py --token 123456789 img1.png img2.png
输出: 每张图的 cdn_url（mmbiz.qpic.cn），JSON 存到 stdout，可重定向保存。
插入正文仍需按 SKILL.md §3.2 图片库 UI 流（合成事件插不了图）。
"""
import argparse
import base64
import json

from raw_cdp import Page, page_targets

UPLOAD_JS = """async ([b64, fname]) => {
    const d = window.wx.commonData.data;
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const file = new File([bytes], fname, {type: 'image/png'});
    const fd = new FormData();
    fd.append('file', file);
    fd.append('error', '');
    fd.append('fromfile', '');
    const url = `https://mp.weixin.qq.com/cgi-bin/filetransfer?action=upload_material`
        + `&f=json&scene=8&writetype=doublewrite&groupid=1`
        + `&ticket_id=${d.uin}&ticket=${d.ticket}&svr_time=${Math.floor(Date.now()/1000)}`
        + `&token=${d.t}&lang=zh_CN&seq=1`;
    const resp = await fetch(url, {method: 'POST', credentials: 'include', body: fd});
    const j = await resp.json();
    return {ok: j.base_resp && j.base_resp.ret === 0, cdn_url: j.cdn_url,
            err: j.base_resp && j.base_resp.err_msg};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("images", nargs="+", help="PNG 文件路径（可多张）")
    args = ap.parse_args()

    pages = [t for t in page_targets() if "appmsg" in t.get("url", "")]
    if not pages:
        print("❌ 编辑器页面未打开，先跑 mp_draft.py")
        raise SystemExit(1)
    page = Page(pages[0], timeout=90)  # 大图 base64 走表达式 + fetch 上传，留足回包时间

    results = {}
    for path in args.images:
        b64 = base64.b64encode(open(path, "rb").read()).decode()
        fname = path.split("/")[-1]
        r = page.ev(f"({UPLOAD_JS})({json.dumps([b64, fname])})", await_promise=True)
        results[fname] = r
        mark = "✅" if r.get("ok") else "❌"
        print(f"{mark} {fname} → {r.get('cdn_url') or r.get('err')}")

    print(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
