#!/bin/bash
# mp_session.sh — 公众号发布前置：起 wechat-mp 场景专用实例（CDP :9227）
# 2026-09-09 起改走 chrome_instance.sh 正规实例（登录态扫码一次持久落盘），
# 旧 /tmp/cdp-mp 全量 cookie 副本链（复制-清理模式，9222）退役。
set -e
exec bash "$HOME/myProject/aiCompany/tools/chrome_instance.sh" start wechat-mp
