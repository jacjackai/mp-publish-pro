#!/usr/bin/env python3
"""mp_draft.py — 公众号编辑器：填标题 + 粘贴正文（裸 CDP 页面级连 9227 wechat-mp 专用实例）

用法:
    python3 mp_draft.py --token 123456789 --title "标题" --html 正文.html
    python3 mp_draft.py --token ... --title ... --html 正文.html --existing  # 复用已打开的编辑器页

正文 HTML 里的 <img> 会被 ProseMirror 丢弃——脚本会报告丢弃数量，
这些图需要按 SKILL.md §3.2 用图片库 UI 流逐个插入。
blockquote/h2-h4 会被过滤，脚本自动简化为 <p>/<strong>。
"""
import argparse
import json
import sys
import time

from raw_cdp import Page, api, page_targets

EDITOR_URL = ("https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2"
              "&action=edit&isNew=1&type=77&token={token}&lang=zh_CN")

SIMPLIFY_JS = (
    "(h => h.replace(/<blockquote[^>]*>/g, '<p>').replace(/<\\/blockquote>/g, '</p>')"
    ".replace(/<(h1|h2|h3|h4)([^>]*)>/g, '<p$2><strong>')"
    ".replace(/<\\/(h1|h2|h3|h4)>/g, '</strong></p>')"
)

PASTE_JS = """async ([title, html]) => {
    for (let i = 0; i < 40; i++) {
        if (document.querySelectorAll('.ProseMirror').length >= 2) break;
        await new Promise(r => setTimeout(r, 500));
    }
    const eds = [...document.querySelectorAll('.ProseMirror')];
    if (eds.length < 2) throw new Error('编辑器未加载完（ProseMirror < 2）');
    // eds[0] = 标题镜像，正文 = parent 含 rich_media_content 的那个——铁律
    const body = eds.find(e => (e.parentElement?.className || '').includes('rich_media_content')) || eds[1];
    const t = document.querySelector('#title');
    t.value = title;
    t.dispatchEvent(new Event('input', {bubbles: true}));
    body.focus();
    await new Promise(r => setTimeout(r, 300));
    const dt = new DataTransfer();
    dt.setData('text/html', html);
    body.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    await new Promise(r => setTimeout(r, 2000));
    return {titleLen: t.value.length,
            bodyLen: body.innerText.length,
            bodyImgs: body.querySelectorAll('img').length};
}"""


def open_editor(token, existing):
    """--existing 时复用已开的编辑器页；否则 PUT /json/new 开新页并等它出现"""
    pages = [t for t in page_targets() if "appmsg" in t.get("url", "")]
    if pages and existing:
        return Page(pages[0])
    api(f"/json/new?{EDITOR_URL.format(token=token)}", "PUT")
    for _ in range(30):
        time.sleep(1)
        pages = [t for t in page_targets() if "appmsg" in t.get("url", "")]
        if pages:
            return Page(pages[0])
    raise SystemExit("❌ 编辑器页 30s 未出现（检查 token 与登录态）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--html", required=True, help="正文 HTML 文件路径")
    ap.add_argument("--existing", action="store_true", help="复用已打开的编辑器页")
    args = ap.parse_args()

    raw = open(args.html, encoding="utf-8").read()
    n_imgs = raw.count("<img")

    page = open_editor(args.token, args.existing)
    simplified = page.ev(f"({SIMPLIFY_JS})({json.dumps(raw)})")
    out = page.ev(f"({PASTE_JS})({json.dumps([args.title, simplified])})",
                  await_promise=True)
    print(json.dumps(out, ensure_ascii=False))

    if out["titleLen"] > 64:
        print("❌ 标题超 64 字")
        sys.exit(1)
    if n_imgs:
        print(f"⚠️ 正文 HTML 含 {n_imgs} 个 <img> 已被编辑器丢弃——按 SKILL.md §3.2 图片库流程逐个插入")


if __name__ == "__main__":
    main()
