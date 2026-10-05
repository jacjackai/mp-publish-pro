#!/usr/bin/env python3
"""mp_code.py — 公众号编辑器「插入代码」功能驱动（CDP 9227 常驻实例）

背景（2026-09-11 实测）：
  编辑器正文里贴 HTML `<pre class="code-snippet__js">` 会被降级成「伪代码块」——
  一个 tagName=pre 的 para 节点，**换行全部丢失**，整段挤成一行，排版全糊。
  正确的做法是走工具栏右侧的「插入代码」按钮：
    1) 该按钮**不弹对话框**，直接在当前光标处插入一个空 codeblock 节点；
    2) 随后把代码以 **text/plain** 粘贴进这个空块，编辑器按行拆成 code 子节点，
       换行、缩进、语法高亮全部正确；语言由编辑器自动识别（无 UI 可改）。
  两个前置条件（缺一不可，2026-09-11 实测）：
    - **标签必须前置**（Page.bringToFront）：后台标签的视口尺寸是错的，工具栏会折叠；
    - **视口要够宽**：窗口最大化后仍不够时，用真实 Cmd+- 缩放一档（视口 ~1600px），
      「插入代码」才会出现在工具栏右侧（x≈1230）而不是被塞进「更多」下拉——
      下拉里那个按钮点了不生效。

用法：
  python3 mp_code.py inspect --mpid 100000074
  python3 mp_code.py repair  --mpid 100000074 --plan plan.json [--dry-run]
  python3 mp_code.py verify  --mpid 100000074 --plan plan.json

plan.json 结构（按正文出现顺序，与伪代码块一一对应）：
  [{"lang": "bash", "code": "第1行\\n第2行"}, ...]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raw_cdp import Page, page_targets  # noqa: E402

SEL_TOOLBAR_CODE = ".edui-for-insertcode"
# 只认顶层 pre：真代码块的 DOM 是 section.code-snippet__js > pre.code-snippet__js，
# 用后代选择器会把已修好的真块也选中（踩过），必须用直接子元素
SEL_FAKE = ".ProseMirror > pre.code-snippet__js"

DUMP_JS = """(()=>{
  const v=window.__mpBodyChecktextView; const rows=[];
  v.state.doc.forEach((n,offset,index)=>{ const a=n.attrs||{};
    rows.push({index, offset, size:n.nodeSize, type:n.type.name, tag:a.tagName||null,
      cls:(a.attributes&&a.attributes.class)||null, nl:/\\n/.test(n.textContent),
      len:n.textContent.length, head:n.textContent.slice(0,48)}); });
  return rows;})()"""

BLOCKS_JS = """(()=>{
  const v=window.__mpBodyChecktextView; const out=[];
  v.state.doc.forEach((n,offset)=>{
    if(n.type.name==='codeblock'){ const lines=[]; n.forEach(c=>lines.push(c.textContent));
      out.push({kind:'codeblock', offset, lang:n.attrs['data-lang'], lines}); }
    else if(n.attrs && n.attrs.tagName==='pre'){ out.push({kind:'fake', offset, size:n.nodeSize,
      cls:(n.attrs.attributes&&n.attrs.attributes.class)||null, lines:[n.textContent]}); }
  });
  return out;})()"""


def pick_tab(mpid=None):
    tabs = [t for t in page_targets() if "mp.weixin.qq.com" in t["url"] and "appmsgid=" in t["url"]]
    if mpid:
        tabs = [t for t in tabs if f"appmsgid={mpid}" in t["url"]] or []
    if not tabs:
        raise SystemExit(f"没有找到 appmsgid={mpid} 的编辑器标签（先手动打开该草稿）")
    return tabs[0]


def connect(mpid=None):
    tab = pick_tab(mpid)
    p = Page(tab, timeout=90)
    p.cmd("Page.bringToFront")          # 铁律①：标签必须前置
    time.sleep(0.6)
    for _ in range(20):
        try:
            if p.ev("!!window.__mpBodyChecktextView"):
                return p
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit("编辑器视图 __mpBodyChecktextView 未就绪")


def click(p, x, y, label=""):
    p.cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "none", "buttons": 0})
    time.sleep(0.08)
    p.cmd("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1, "buttons": 1})
    time.sleep(0.06)
    p.cmd("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1, "buttons": 0})
    if label:
        print(f"      · 点击 {label} @({x:.0f},{y:.0f})")


def key(p, k, code, vk):
    for t in ("keyDown", "keyUp"):
        p.cmd("Input.dispatchKeyEvent", {"type": t, "modifiers": 0, "key": k, "code": code,
                                         "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk})


def toolbar_rect(p):
    return p.ev(f"""(()=>{{
      const vis=[...document.querySelectorAll('{SEL_TOOLBAR_CODE}')].filter(e=>e.getClientRects().length);
      if(!vis.length) return null; const b=vis[0].getBoundingClientRect();
      return {{x:b.x+b.width/2, y:b.y+b.height/2}};}})()""")


def ensure_toolbar_button(p, allow_zoom=True):
    """铁律②：视口够宽时「插入代码」才在工具栏右侧；不够就放大窗口/缩放一档"""
    r = toolbar_rect(p)
    if r:
        return r
    print("    · 工具栏未显示「插入代码」，尝试放大视口")
    p.ev("window.moveTo(0,0); window.resizeTo(screen.width, screen.height);")
    time.sleep(1.0)
    r = toolbar_rect(p)
    if r:
        return r
    if not allow_zoom:
        return None
    for _ in range(3):
        for t in ("keyDown", "keyUp"):
            p.cmd("Input.dispatchKeyEvent", {"type": t, "modifiers": 4, "key": "-", "code": "Minus",
                                             "windowsVirtualKeyCode": 189, "nativeVirtualKeyCode": 27,
                                             "text": "-" if t == "keyDown" else ""})
        time.sleep(1.0)
        r = toolbar_rect(p)
        w = p.ev("innerWidth")
        print(f"    · 缩放一档后视口宽 {w}")
        if r:
            return r
    return None


def paste_text(p, text, label=""):
    return p.ev("""(()=>{const dt=new DataTransfer(); dt.setData('text/plain',%s);
      const t=document.activeElement;
      t.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));
      return (t.className||'').toString().slice(0,40);})()""" % json.dumps(text))


def cmd_inspect(p):
    print(json.dumps({"blocks": p.ev(BLOCKS_JS), "nodes": p.ev(DUMP_JS)}, ensure_ascii=False, indent=1))


def strip_ws(s):
    """去掉全部空白（含 &nbsp; 转出的 \\u00a0）用于内容匹配"""
    return re.sub(r"\s+", "", s or "")


def find_fake_rect(p, code):
    """按内容定位伪代码块 → 滚动进视口 → 返回可点击坐标（返回 matched 标记）"""
    key = strip_ws(code)
    return p.ev(f"""(()=>{{
      const key={json.dumps(key)};
      const strip=s=>(s||'').replace(/\\s+/g,'').replace(/\\u00a0/g,'');
      const els=[...document.querySelectorAll('{SEL_FAKE}')];
      if(!els.length) return null;
      let hit=els.find(e=>strip(e.textContent)===key);
      const matched=!!hit;
      if(!hit) hit=els[0];
      const h0=hit.getBoundingClientRect().height;
      hit.scrollIntoView({{block: h0 > innerHeight*0.6 ? 'start' : 'center'}});
      const r=hit.getBoundingClientRect();
      // 安全区：工具栏是吸顶的（底边约 y=100），点击必须落在它下面，否则会点到工具栏
      const tb=document.querySelector('.edui-editor-toolbarbox, #js_editor_toolbarbox');
      const safeTop=Math.max(130, tb ? tb.getBoundingClientRect().bottom + 20 : 130);
      const x=Math.max(r.x+6, 5);
      const y=Math.min(Math.max(r.y+12, safeTop), innerHeight-40);
      return {{x, y, matched, rectTop:Math.round(r.y), rectH:Math.round(h0), safeTop:Math.round(safeTop)}};}})()""")


def cursor_in_fake(p):
    """校验当前光标是否落在伪代码块（para[tagName=pre]）内部"""
    return p.ev("""(()=>{const v=window.__mpBodyChecktextView;const $f=v.state.selection.$from;
      const path=[];for(let d=$f.depth;d>=0;d--){const n=$f.node(d);
        path.push(n.type.name + (n.attrs&&n.attrs.tagName? ':'+n.attrs.tagName : ''));}
      return path;})()""")


def cmd_repair(p, plan, dry_run=False, pace=1.6):
    total = len(plan)
    print(f"计划修复 {total} 处代码块")
    if dry_run:
        for i, b in enumerate(plan):
            code = b["code"]
            print(f"  [{i}] lang={b.get('lang')} 行数={len(code.splitlines())} 字符={len(code)}")
        return
    done = []          # 本次成功替换掉的块（清理只针对它们）
    for i, b in enumerate(plan):
        code = b["code"].rstrip("\n")
        print(f"  [{i+1}/{total}] {len(code.splitlines())} 行")
        # 1) 按内容定位对应的伪代码块
        fake = find_fake_rect(p, code)
        if not fake:
            print("      !! 找不到伪代码块，跳过"); continue
        if not fake.get("matched"):
            print("      !! 内容未匹配上，回落到第一个伪块（请核对）")
        before = p.ev("""(()=>{let n=0;window.__mpBodyChecktextView.state.doc.forEach(x=>{if(x.type.name==='codeblock')n++;});return n;})()""")
        # 2) 真点进伪块 + Home 归位（让「插入代码」把它从光标处切开）
        #    点前命中校验：该坐标上必须是伪块本身或其后代（防止点到工具栏/浮层，静默失败）
        hit = p.ev("""(()=>{const e=document.elementFromPoint(%s, %s);
          return e? {tag:e.tagName, cls:(e.className||'').toString().slice(0,40),
                     inFake: !!e.closest('pre.code-snippet__js')} : null;})()""" % (fake["x"], fake["y"]))
        if not hit or not hit.get("inFake"):
            print(f"      !! 点击坐标未命中伪块（{json.dumps(hit, ensure_ascii=False)}），跳过本处")
            continue
        click(p, fake["x"], fake["y"], "伪代码块内")
        time.sleep(0.5)
        path = cursor_in_fake(p)
        # 伪块的模型结构是 para[tagName=pre] > code > leaf > 文本，光标路径里必有 para:pre
        if "para:pre" not in path:
            print(f"      !! 光标未落在伪代码块内（{path}），跳过本处，不做改动")
            continue
        key(p, "Home", "Home", 36)
        time.sleep(0.3)
        # 3) 真点工具栏「插入代码」
        btn = ensure_toolbar_button(p)
        if not btn:
            print("      !! 「插入代码」按钮不可见，中止"); return
        click(p, btn["x"], btn["y"], "插入代码")
        time.sleep(1.0)
        after = p.ev("""(()=>{let n=0;window.__mpBodyChecktextView.state.doc.forEach(x=>{if(x.type.name==='codeblock')n++;});return n;})()""")
        if after != before + 1:
            print(f"      !! 代码块数量未增加（{before}→{after}），中止"); return
        # 4) 纯文本粘贴进空代码块
        paste_text(p, code)
        time.sleep(1.2)
        cur = p.ev("""(()=>{const out=[];window.__mpBodyChecktextView.state.doc.forEach(x=>{
            if(x.type.name==='codeblock'){let n=0;x.forEach(()=>n++);out.push({lang:x.attrs['data-lang'],lines:n});}});return out;})()""")
        print(f"      → 代码块现状: {json.dumps(cur, ensure_ascii=False)}")
        done.append(strip_ws(code))
        time.sleep(pace)
    # 5) 清理残留伪代码块 —— 只删「本次成功替换掉的那几块」左右紧邻的伪块，
    #    绝不做无差别清理（踩过：一处都没成功时把正文代码全删了）
    if not done:
        print("  没有成功替换的代码块，跳过清理（不做任何删除）")
        return
    removed = p.ev("""(()=>{
      const v=window.__mpBodyChecktextView, doc=v.state.doc;
      const keys=%s, strip=s=>(s||'').replace(/\\s+/g,'').replace(/\\u00a0/g,'');
      const kids=[]; doc.forEach((n,offset)=>kids.push({n,offset}));
      const ranges=[];
      kids.forEach((k,i)=>{
        if(k.n.type.name!=='codeblock') return;
        if(!keys.includes(strip(k.n.textContent))) return;
        for(let j=i-1;j>=0;j--){ const s=kids[j]; if(s.n.attrs&&s.n.attrs.tagName==='pre') ranges.push([s.offset,s.offset+s.n.nodeSize]); else break; }
        for(let j=i+1;j<kids.length;j++){ const s=kids[j]; if(s.n.attrs&&s.n.attrs.tagName==='pre') ranges.push([s.offset,s.offset+s.n.nodeSize]); else break; }
      });
      if(!ranges.length) return 0;
      let tr=v.state.tr;
      ranges.sort((a,b)=>b[0]-a[0]).forEach(r=>{ tr=tr.delete(r[0],r[1]); });
      v.dispatch(tr); return ranges.length;})()""" % json.dumps(done))
    print(f"  清理残留伪代码块: {removed} 个（共成功替换 {len(done)}/{total} 处）")


def cmd_verify(p, plan):
    blocks = p.ev(BLOCKS_JS)
    real = [b for b in blocks if b["kind"] == "codeblock"]
    fake = [b for b in blocks if b["kind"] == "fake"]
    ok = True
    print(f"真代码块 {len(real)} 个 / 残留伪代码块 {len(fake)} 个")
    if fake:
        ok = False
        print("  ✘ 仍有伪代码块:", json.dumps(fake, ensure_ascii=False)[:300])
    if plan:
        if len(real) != len(plan):
            ok = False
            print(f"  ✘ 数量不符：期望 {len(plan)}，实际 {len(real)}")
        for i, (b, expect) in enumerate(zip(real, plan)):
            exp_lines = expect["code"].rstrip("\n").split("\n")
            got = [l.rstrip() for l in b["lines"]]
            exp = [l.rstrip() for l in exp_lines]
            # 编辑器末尾可能多一个空行
            while got and got[-1] == "":
                got.pop()
            same = got == exp
            ok = ok and same
            print(f"  {'✔' if same else '✘'} [{i}] lang={b['lang']} 行数 {len(got)}/{len(exp)}")
            if not same:
                for j, (g, e2) in enumerate(zip(got, exp)):
                    if g != e2:
                        print(f"      行{j+1} 差异:\n        实际: {g[:90]}\n        期望: {e2[:90]}")
                        break
    print("结论:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["inspect", "repair", "verify"])
    ap.add_argument("--mpid")
    ap.add_argument("--plan")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pace", type=float, default=1.6, help="每处之间的停顿秒数（动作放慢，降低被判定为插件的风险）")
    a = ap.parse_args()

    plan = None
    if a.plan:
        plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    p = connect(a.mpid)
    if a.cmd == "inspect":
        cmd_inspect(p)
    elif a.cmd == "repair":
        if not plan:
            raise SystemExit("repair 需要 --plan")
        cmd_repair(p, plan, dry_run=a.dry_run, pace=a.pace)
    else:
        sys.exit(cmd_verify(p, plan))


if __name__ == "__main__":
    main()
