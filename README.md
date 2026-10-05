# mp-publish-pro · 公众号自动发布技能

让 AI 编码 agent（Claude Code / OpenCode / Codex / Cursor 等）驱动 Chrome，完成微信公众号文章的
建草稿、配图、封面裁剪、发表前置设置直至扫码发表的全流程自动化。

本体是一份 Agent Skills 标准格式的 `SKILL.md`（操作剧本）+ 辅助脚本，执行层依赖开源的
[Tencent BrowserSkill](https://github.com/Tencent/BrowserSkill)（MIT，见 `NOTICE.md`）。

## 购买后安装

### 方式一：skills CLI（Claude Code / OpenCode / Codex / Cursor 等）

```bash
npx skills add <仓库地址> --skill wechat-mp-publish
```

安装器自动探测本机 agent 并放到正确目录。

### 方式二：手动安装（任意 agent，含 Qoder 等不加载技能格式的）

把 `skills/wechat-mp-publish/` 整个目录拷到 agent 的技能目录
（Claude Code：`~/.claude/skills/`；OpenCode：`~/.config/opencode/skills/`，其余同理），
或在首次对话里直接要求：

> 发公众号前，先完整阅读 skills/wechat-mp-publish/SKILL.md 并严格按它执行。

## 环境要求（缺一不可，缺哪个 agent 会卡在哪步）

1. **bsk** CLI：按 [官方安装指南](https://github.com/Tencent/BrowserSkill/blob/main/AGENT_INSTALL.md) 安装，
   `bsk doctor` 全绿再开工。**禁止 `bsk update --yes`**（版本以 SKILL.md pin 为准）。
2. **Chrome + BrowserSkill 扩展**：安装指南第 4 步，扩展连上后 `bsk browsers` 能看到浏览器。
3. **公众号登录态**：`bsk navigate "https://mp.weixin.qq.com/"` 后落扫码页即需人工扫码一次，
   登录态随后按 Chrome profile 持久。
4. **用户配置**：复制 `skills/wechat-mp-publish/user.conf.example` 为同目录 `user.conf` 并填写
   （原创作者名必填；合集、赞赏账户可留空跳过）。
5. **授权激活**：`license.key` 已随交付包放在 `skills/wechat-mp-publish/scripts/` 目录
   （如需手动放置，也是放这个目录），
   跑 `python3 skills/wechat-mp-publish/scripts/license_check.py`，看到「已授权」即可开工；
   以后每次发表 agent 都会先过这道校验。

## 使用

对 agent 说「发公众号 / 把这篇发到公众号 / 更新公众号」即可触发；会话结束时 agent 应执行
`bsk session stop` 收尾。发表环节的微信扫码必须由账号本人完成，技能会在扫码浮层处停下等待。

## 授权

- 正版授权 = 私有仓库访问权 + 每份交付副本带购买者水印，禁止二次分发（详见随订单的授权条款）。
- 买断含交付时点版本的全部功能；后续版本更新按年订阅（在原购买渠道续订即可继续 `git pull`）。
