#!/bin/sh
# mp-publish-pro 环境一键安装 + 体检门槛（可重复跑；装不上带着输出提 issue）
# 干的事：装 bsk CLI（钉实测版）→ 查 Chrome → bsk doctor 当闸 → 提示剩两步
# 不干的事：不装技能本体（那是 npx skills add / 手动拷贝）、不碰登录态（扫码永远本人）
set -eu

PIN="0.3.2"
UPSTREAM_INSTALL="https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh"
STORE="https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi"

c_info() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
c_ok()   { printf '\033[32m✅\033[0m %s\n' "$1"; }
c_warn() { printf '\033[33m⚠️  %s\033[0m\n' "$1"; }
c_die()  { printf '\033[31m❌ %s\033[0m\n' "$1" >&2; exit 1; }

c_info "mp-publish-pro 环境安装（bsk pin ${PIN}）"

# 1) 系统平台
case "$(uname -s)" in
  Darwin) os=mac ;;
  Linux)  os=linux ;;
  *) c_die "本脚本支持 macOS/Linux。Windows 用 PowerShell 装 bsk：irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex，再按 README 手动完成其余步骤（本产品 Windows 未实测）。" ;;
esac

# 2) Chrome
if [ "$os" = mac ]; then
  [ -d "/Applications/Google Chrome.app" ] || c_die "没找到 Chrome：https://www.google.com/chrome/ 装好后重跑本脚本。"
else
  command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1 \
    || command -v chromium >/dev/null 2>&1 || c_die "没找到 Chrome/Chromium：https://www.google.com/chrome/ 装好后重跑本脚本。"
fi
c_ok "Chrome 已安装"

# 3) bsk CLI（0.3.x 实测线；已有装新装钉版）
BSK=""
if command -v bsk >/dev/null 2>&1; then BSK="$(command -v bsk)"
elif [ -x "$HOME/.local/bin/bsk" ]; then BSK="$HOME/.local/bin/bsk"
fi
if [ -z "$BSK" ]; then
  c_info "安装 bsk CLI（钉 $PIN）"
  curl -fsSL "$UPSTREAM_INSTALL" | BSK_VERSION="$PIN" sh
  BSK="$HOME/.local/bin/bsk"
  [ -x "$BSK" ] || c_die "安装后未找到 ${BSK}：把 $HOME/.local/bin 加入 PATH 后重跑本脚本。"
fi
VNUM="$("$BSK" --version 2>/dev/null | tail -1 || true)"
VNUM="${VNUM#bsk }"
case "$VNUM" in
  0.3.*) c_ok "bsk ${VNUM}（符合 0.3.x 实测线）" ;;
  "")    c_warn "bsk --version 无输出，安装可能不完整，继续跑 doctor 验证。" ;;
  *)     c_warn "bsk 是 ${VNUM}，本产品只在 0.3.x 实测。异常请钉版重装：curl -fsSL $UPSTREAM_INSTALL | BSK_VERSION=${PIN} sh" ;;
esac

# 4) doctor 门槛（扩展连接、协议兼容、daemon 都在里面查）
c_info "运行 bsk doctor 体检"
if "$BSK" doctor; then
  c_ok "doctor 全绿"
else
  printf '\n'
  c_warn "doctor 没全绿，上面带 fail 的行就是卡点。最常见两种："
  printf '   · extension connected 失败 → 先在 Chrome 装扩展：%s\n' "$STORE"
  printf '     装好打开扩展弹窗启用本地连接，再重跑本脚本\n'
  printf '   · daemon 相关失败 → 重跑一次本脚本（首跑会自动拉起）\n'
  exit 1
fi

# 5) 剩两步
c_info "环境就绪。剩下两步："
if command -v npx >/dev/null 2>&1; then
  printf '   1. 装技能本体：npx skills add jacjackai/mp-publish-pro --skill wechat-mp-publish\n'
else
  printf '   1. 未检测到 npx（Node.js）：装 Node 后用上面命令，或按 README 用 git clone 手动装技能\n'
fi
printf '   2. 复制 skills/wechat-mp-publish/user.conf.example 为同目录 user.conf 填好，\n'
printf '      然后对 agent 说：把这篇发到公众号（首次进后台要扫码，发表前还要再扫一次，都用你本人手机）\n'
