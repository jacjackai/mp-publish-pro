#!/usr/bin/env python3
"""给草稿设置封面（图片库 UI 流）——每步现测坐标，避免用到过期 rect"""
import sys, json, time
sys.path.insert(0, '/Users/jack/.agents/skills/wechat-mp-publish/scripts')
from raw_cdp import Page, page_targets

MPID = sys.argv[1] if len(sys.argv) > 1 else "100000074"
COVER_NAME = sys.argv[2] if len(sys.argv) > 2 else "cover_2.35.png"

def click(p, x, y, label):
    p.cmd("Input.dispatchMouseEvent", {"type":"mouseMoved","x":x,"y":y,"button":"none","buttons":0}); time.sleep(0.1)
    p.cmd("Input.dispatchMouseEvent", {"type":"mousePressed","x":x,"y":y,"button":"left","clickCount":1,"buttons":1}); time.sleep(0.08)
    p.cmd("Input.dispatchMouseEvent", {"type":"mouseReleased","x":x,"y":y,"button":"left","clickCount":1,"buttons":0})
    print(f"    · 点击 {label} @({x:.0f},{y:.0f})")

def click_el(p, expr, label):
    """现测坐标 + 命中校验（防止点到遮罩把对话框关掉），返回是否点中"""
    info = p.ev("""(()=>{const e=%s; if(!e||!e.getClientRects().length) return null;
      e.scrollIntoView({block:'center', inline:'nearest'});
      const b=e.getBoundingClientRect(); const x=b.x+b.width/2, y=b.y+b.height/2;
      if(y<0||y>innerHeight||x<0||x>innerWidth) return {x,y,hit:false,topCls:'(视口外)',vh:innerHeight};
      const top=document.elementFromPoint(x,y);
      return {x, y, hit: !!top && (e===top || e.contains(top)), topCls:(top&&top.className||'').toString().slice(0,60),
              vh:innerHeight};})()""" % expr)
    if not info:
        print(f"    !! {label} 不可见/不存在"); return False
    if not info['hit']:
        print(f"    !! {label} 命中校验失败（该点上是 {info['topCls']}），不点"); return False
    click(p, info['x'], info['y'], label)
    return True


def rect_of(p, expr):
    return p.ev("""(()=>{const e=%s; if(!e) return null; const b=e.getBoundingClientRect();
      if(!e.getClientRects().length) return null;
      return {x:b.x+b.width/2, y:b.y+b.height/2, w:Math.round(b.width), h:Math.round(b.height), vh:innerHeight};})()""" % expr)

def vis_dialog(p):
    return p.ev("""(()=>{const vis=e=>!!(e.getClientRects&&e.getClientRects().length);
      const d=[...document.querySelectorAll('.weui-desktop-dialog__wrp')].filter(vis)[0];
      if(!d) return null;
      return {title:(d.querySelector('.weui-desktop-dialog__title')||{}).innerText||'',
              text:(d.innerText||'').replace(/\\n+/g,'|').slice(0,120)};})()""")

def cover_state(p):
    return p.ev("""(()=>{const slot=document.querySelector('#js_cover_area');
      const img=slot? slot.querySelector('img'):null;
      let cd=null; try{ cd=window.wx.commonData.data; }catch(e){}
      return {rendered: !!img, src: img? img.src.slice(0,60):null,
              placeholder:(slot?slot.innerText:'').replace(/\\n/g,'|').slice(0,40),
              cover_media_id: cd? (cd.cover_media_id||null):null};})()""")

def main():
    tab=[t for t in page_targets() if f'appmsgid={MPID}' in t['url']][0]
    p=Page(tab, timeout=90)
    p.cmd("Page.bringToFront"); time.sleep(0.6)

    st=cover_state(p)
    print("初始封面态:", json.dumps(st, ensure_ascii=False))
    if st['rendered']:
        print("已有封面，结束"); return

    # 1) 点封面槽 → 菜单
    if not click_el(p, "document.querySelector('.js_cover_btn_area')||document.querySelector('#js_cover_area')", "封面槽"):
        return
    time.sleep(1.2)

    # 2) 从图片库选择
    if not click_el(p, "document.querySelector('#js_cover_null .js_imagedialog')", "从图片库选择"):
        return
    time.sleep(2.5)
    print("   对话框:", json.dumps(vis_dialog(p), ensure_ascii=False))

    # 3) 选目标图（先确保在「最近使用」标签）
    card_expr = ("[...document.querySelectorAll('.weui-desktop-img-picker__item')]"
                 f".find(e=>(e.innerText||'').includes({COVER_NAME!r}))")
    if not click_el(p, card_expr, COVER_NAME):
        print("    !! 图库里没找到或点不中", COVER_NAME); return
    time.sleep(1.0)
    sel=p.ev("""(()=>{const vis=e=>!!(e.getClientRects&&e.getClientRects().length);
      const d=[...document.querySelectorAll('.weui-desktop-dialog__wrp')].filter(vis)[0];
      return [...d.querySelectorAll('.weui-desktop-img-picker__item')].filter(e=>/selected/.test(e.className))
        .map(e=>(e.innerText||'').replace(/\\n/g,'|').slice(0,30));})()""")
    print("   已选中:", json.dumps(sel, ensure_ascii=False))
    if not sel:
        print("!! 卡片未被选中，中止"); return

    # 4) 下一步（现测坐标）
    if not click_el(p, "[...document.querySelectorAll('.weui-desktop-dialog__wrp button')].filter(b=>b.getClientRects().length && b.innerText.trim()==='下一步')[0]", "下一步"):
        return
    time.sleep(2.5)
    print("   裁剪页:", json.dumps(vis_dialog(p), ensure_ascii=False))

    # 5) 确认（现测坐标 + 视口内校验，必要时缩一档）
    def confirm_rect():
        return rect_of(p, "[...document.querySelectorAll('.weui-desktop-dialog__wrp button')].filter(b=>b.getClientRects().length && b.innerText.trim()==='确认')[0]")
    r=confirm_rect()
    if not r:
        print("!! 没找到「确认」"); return
    if r['y'] > r['vh'] - 40:
        print(f"   确认按钮贴底(y={r['y']:.0f}/vh={r['vh']})，缩一档视口")
        for t in ("keyDown","keyUp"):
            p.cmd("Input.dispatchKeyEvent", {"type":t,"modifiers":4,"key":"-","code":"Minus",
                   "windowsVirtualKeyCode":189,"nativeVirtualKeyCode":27,"text":"-" if t=="keyDown" else ""})
        time.sleep(1.2)
        r=confirm_rect()
        print("   缩放后确认按钮:", json.dumps(r, ensure_ascii=False))
    print(f"   确认按钮 rect={r} 视口高={r['vh']}")
    if not click_el(p, "[...document.querySelectorAll('.weui-desktop-dialog__wrp button')].filter(b=>b.getClientRects().length && b.innerText.trim()==='确认')[0]", "确认"):
        return
    time.sleep(3.0)

    print("对话框是否还在:", json.dumps(vis_dialog(p), ensure_ascii=False)[:120])
    st=cover_state(p)
    print("设置后封面态:", json.dumps(st, ensure_ascii=False))

if __name__ == '__main__':
    main()
