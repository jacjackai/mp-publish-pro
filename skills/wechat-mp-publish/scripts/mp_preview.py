#!/usr/bin/env python3
"""发送预览到预置微信号（默认 shuguodang），并抓包确认"""
import sys, json, time
sys.path.insert(0, '/Users/jack/.agents/skills/wechat-mp-publish/scripts')
from raw_cdp import Page, page_targets

MPID = sys.argv[1] if len(sys.argv) > 1 else "100000074"

class Sniffer(Page):
    def drain(self, seconds=1.0):
        out=[]; end=time.time()+seconds; self.ws.settimeout(0.3)
        while time.time()<end:
            try: m=json.loads(self.ws.recv())
            except Exception: continue
            if 'method' in m: out.append(m)
        self.ws.settimeout(60); return out

def click_el(p, expr, label):
    info=p.ev("""(()=>{const e=%s; if(!e||!e.getClientRects().length) return null;
      const b=e.getBoundingClientRect(); const x=b.x+b.width/2, y=b.y+b.height/2;
      const top=document.elementFromPoint(x,y);
      return {x,y,hit:!!top&&(e===top||e.contains(top)),topTxt:(top&&top.innerText||'').trim().slice(0,12)};})()""" % expr)
    if not info or not info['hit']:
        print("  !! 点不中", label, json.dumps(info, ensure_ascii=False)); return False
    p.cmd("Input.dispatchMouseEvent",{"type":"mouseMoved","x":info['x'],"y":info['y'],"button":"none","buttons":0}); time.sleep(0.12)
    p.cmd("Input.dispatchMouseEvent",{"type":"mousePressed","x":info['x'],"y":info['y'],"button":"left","clickCount":1,"buttons":1}); time.sleep(0.12)
    p.cmd("Input.dispatchMouseEvent",{"type":"mouseReleased","x":info['x'],"y":info['y'],"button":"left","clickCount":1,"buttons":0})
    print(f"  · 点击 {label}")
    return True

def main():
    tab=[t for t in page_targets() if f'appmsgid={MPID}' in t['url']][0]
    p=Sniffer(tab, timeout=90)
    p.cmd("Page.bringToFront"); time.sleep(0.5)
    p.cmd("Network.enable")

    st=p.ev("""(()=>{const vis=e=>!!(e.getClientRects&&e.getClientRects().length);
      const d=[...document.querySelectorAll('.weui-desktop-dialog__wrp')].filter(vis)[0];
      if(!d) return {open:false};
      const tags=[...d.querySelectorAll('[class*=tag]')].filter(vis).map(e=>(e.innerText||'').replace(/\\n/g,'|').trim()).filter(Boolean);
      return {open:true, title:(d.querySelector('.weui-desktop-dialog__title')||{}).innerText, tags};})()""")
    print("预览弹窗:", json.dumps(st, ensure_ascii=False))
    if not st.get('open'):
        print("!! 弹窗不在了，请重开预览弹窗"); return

    p.drain(0.4)
    if not click_el(p, "[...document.querySelectorAll('.weui-desktop-dialog__wrp button')].filter(b=>b.getClientRects().length&&b.innerText.trim()==='确定')[0]", "确定"):
        return
    evs=p.drain(8.0)

    reqs={}
    for e in evs:
        m=e.get('method'); pr=e.get('params',{})
        if m=='Network.requestWillBeSent':
            reqs[pr['requestId']]={'url':pr['request']['url'][:110],'method':pr['request']['method'],
                                   'post':(pr['request'].get('postData') or '')[:200]}
        elif m=='Network.responseReceived':
            rid=pr['requestId']
            if rid in reqs: reqs[rid]['status']=pr['response']['status']
    print("=== 相关请求 ===")
    for v in reqs.values():
        if any(k in v['url'] for k in ('preview','appmsg','operate')):
            print("  ", json.dumps(v, ensure_ascii=False))
    time.sleep(2)
    print("弹窗是否关闭:", p.ev("""(()=>{const vis=e=>!!(e.getClientRects&&e.getClientRects().length);
      return [...document.querySelectorAll('.weui-desktop-dialog__wrp')].filter(vis).map(d=>(d.querySelector('.weui-desktop-dialog__title')||{}).innerText||'(无题)');})()"""))
    print("提示/toast:", json.dumps(p.ev("""(()=>{const vis=e=>!!(e.getClientRects&&e.getClientRects().length);
      return [...document.querySelectorAll('[class*=toast],[class*=tips]')].filter(vis).map(e=>(e.innerText||'').trim().slice(0,80)).filter(Boolean).slice(0,5);})()"""), ensure_ascii=False))

if __name__=='__main__':
    main()
