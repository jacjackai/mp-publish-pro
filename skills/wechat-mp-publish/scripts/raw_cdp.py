#!/usr/bin/env python3
"""raw_cdp.py — wechat-mp-publish 共享裸 CDP 传输层（页面级 WebSocket 直连）

Chrome 152 起拒绝浏览器级 attach（Playwright connect_over_cdp 握手即被拒），
页面级连接不受影响（2026-09-10 实测 9227 实例 Chrome/152.0.7977.83 可用）。
本模块只管传输，业务逻辑（选页、导航、等待、铁律 JS）归各脚本：
  api() / page_targets()  — HTTP 控制端点（/json/list、/json/new、/json/close）
  Page                    — 页面级 WebSocket：cmd() 发 CDP 指令，ev() 跑 JS 拿返回值
"""
import json
import urllib.request

import websocket

CDP = "http://127.0.0.1:9227"


def api(path, method=None):
    """调 CDP HTTP 端点；开新 tab 用 api('/json/new?<url>', 'PUT')"""
    url = f"{CDP}{path}"
    req = urllib.request.Request(url, method=method) if method else url
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def page_targets():
    return [t for t in api("/json/list") if t.get("type") == "page"]


class Page:
    """连接单个页面 target 的裸 CDP 会话（suppress_origin：Chrome 拒带 Origin 的握手）"""

    def __init__(self, target, timeout=60):
        self.target = target
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"],
                                              timeout=timeout, suppress_origin=True)
        self.mid = 0

    def cmd(self, method, params=None):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params or {}}))
        while True:  # 跳过事件帧，只认本次调用的应答
            m = json.loads(self.ws.recv())
            if m.get("id") == self.mid:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    def ev(self, expr, await_promise=False):
        """页面里求值 JS 表达式，返回值反序列化回 Python；JS 抛错则 RuntimeError"""
        r = self.cmd("Runtime.evaluate", {"expression": expr, "awaitPromise": await_promise,
                                          "returnByValue": True})
        res = r.get("result", {})
        if r.get("exceptionDetails") or res.get("subtype") == "error":
            desc = (r.get("exceptionDetails", {}).get("exception", {}).get("description")
                    or res.get("description") or "evaluate 失败")
            raise RuntimeError(f"evaluate: {desc[:300]}")
        return res.get("value")
