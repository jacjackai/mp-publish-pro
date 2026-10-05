#!/usr/bin/env python3
"""按 appmsgid 精确删除草稿（接口取自页面 JS：operate_appmsg?sub=del，参数 AppMsgId）

安全闸：
  1) 硬编码保护 KEEP_IDS，绝不删（默认保护 100000074 = 修好的那篇）
  2) 删之前先拉列表，核对该 id 存在且 update_time 与预期一致
  3) 每删一篇立刻重新拉列表复核：目标消失、保护对象仍在
用法: python3 mp_del_by_id.py 100000077 100000073 100000070
"""
import sys, json, time, datetime
sys.path.insert(0, '/Users/jack/.agents/skills/wechat-mp-publish/scripts')
from raw_cdp import Page, page_targets

KEEP_IDS = {100000074}
EXPECT = {100000070: ("09-11 10:19", "有封面"), 100000073: ("09-11 10:37", "无封面"),
          100000077: ("09-11 14:15", "无封面")}

LIST_JS = """(async()=>{
  const tok=new URLSearchParams(location.search).get('token');
  const r=await fetch('/cgi-bin/appmsg?begin=0&count=30&type=77&action=list_ex&token='+tok+'&lang=zh_CN&f=json&ajax=1&_='+Date.now(),
     {credentials:'include',cache:'no-store',headers:{'x-requested-with':'XMLHttpRequest'}});
  const j=await r.json();
  return (j.app_msg_list||[]).map(x=>({id:x.appmsgid, title:(x.title||'(未命名)'), cover:!!(x.cover||''), ut:x.update_time}));
})()"""

DEL_JS = """(async(id)=>{
  const tok=new URLSearchParams(location.search).get('token');
  const body=new URLSearchParams({AppMsgId:String(id)}).toString();
  const r=await fetch('/cgi-bin/operate_appmsg?sub=del&t=ajax-response&token='+tok+'&lang=zh_CN&f=json&ajax=1',
     {method:'POST', credentials:'include',
      headers:{'Content-Type':'application/x-www-form-urlencoded','x-requested-with':'XMLHttpRequest'},
      body});
  const txt=await r.text();
  let j=null; try{ j=JSON.parse(txt);}catch(e){}
  return {status:r.status, ret: j&&j.base_resp? j.base_resp.ret : null,
          errmsg: j&&j.base_resp? j.base_resp.err_msg : null, raw: j? null : txt.slice(0,150)};
})"""

def show(rows):
    for x in rows:
        t=datetime.datetime.fromtimestamp(x['ut']).strftime('%m-%d %H:%M')
        print(f"     {x['id']}  更新 {t}  {'封面' if x['cover'] else '无封面'}  {x['title'][:30]}")

def main():
    targets=[int(a) for a in sys.argv[1:]]
    bad=[t for t in targets if t in KEEP_IDS]
    if bad:
        raise SystemExit(f"拒绝执行：目标里含保护 id {bad}")
    tab=[t for t in page_targets() if 'appmsgid=100000074' in t['url']][0]
    p=Page(tab, timeout=60)
    p.cmd("Page.bringToFront"); time.sleep(0.4)

    rows=p.ev(LIST_JS, await_promise=True)
    print("删除前，草稿箱："); show(rows)

    for tid in targets:
        cur=[x for x in rows if x['id']==tid]
        if not cur:
            print(f"\n[{tid}] 不存在，跳过"); continue
        x=cur[0]
        stamp=datetime.datetime.fromtimestamp(x['ut']).strftime('%m-%d %H:%M')
        exp=EXPECT.get(tid)
        if exp:
            want_time, want_cover = exp
            got_cover = "有封面" if x['cover'] else "无封面"
            if stamp!=want_time or got_cover!=want_cover:
                print(f"\n[{tid}] !! 预期不符（预期 {want_time}/{want_cover}，实际 {stamp}/{got_cover}），跳过")
                continue
        print(f"\n[{tid}] 准备删除：更新 {stamp}，{'有封面' if x['cover'] else '无封面'}，{x['title'][:30]}")
        res=p.ev(f"({DEL_JS})({tid})", await_promise=True)
        print("     接口返回:", json.dumps(res, ensure_ascii=False))
        time.sleep(2.0)
        rows=p.ev(LIST_JS, await_promise=True)
        gone = tid not in [x['id'] for x in rows]
        keep_ok = all(k in [x['id'] for x in rows] for k in KEEP_IDS)
        print(f"     复核：目标已消失={gone}  保护对象仍在={keep_ok}  剩余 {len(rows)} 篇")
        show(rows)
        if not gone or not keep_ok:
            print("     !! 复核不通过，停止后续删除"); break
    print("\n完成。")

if __name__=='__main__':
    main()
