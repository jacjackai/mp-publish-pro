# mp-publish-pro · 公众号自动发布技能

让 AI 编码 agent（Claude Code / OpenCode / Codex / Cursor 等）驱动 Chrome，完成微信公众号文章的
建草稿、配图、封面裁剪、发表前置设置直至扫码发表的全流程自动化。

本体是一份 Agent Skills 标准格式的 `SKILL.md`（操作剧本）+ 辅助脚本，执行层依赖开源的
[Tencent BrowserSkill](https://github.com/Tencent/BrowserSkill)（MIT，见 `NOTICE.md`）。

## 安装

### 方式一：skills CLI（Claude Code / OpenCode / Codex / Cursor 等）

```bash
npx skills add jacjackai/mp-publish-pro --skill wechat-mp-publish
```

安装器自动探测本机 agent 并放到正确目录；更新重跑同一条命令即可。

### 方式二：git clone + 手动安装（任意 agent，含 Qoder 等不加载技能格式的）

```bash
git clone https://github.com/jacjackai/mp-publish-pro.git
```

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

## 使用

对 agent 说「发公众号 / 把这篇发到公众号 / 更新公众号」即可触发；会话结束时 agent 应执行
`bsk session stop` 收尾。发表环节的微信扫码必须由账号本人完成，技能会在扫码浮层处停下等待。

## 收费方式：请喝咖啡

全功能、永久免费、没有任何锁——每次发表全流程都能跑。

如果它确实替你省了工夫，可以 9.9 元请作者喝杯咖啡：用满 3 次后会不定期提醒
（首次必提，之后大约每 2~5 次出现一次，含微信二维码，agent 会展示给你）。
**付过的人作者会回发一个 `license.key`**，放进 `skills/wechat-mp-publish/scripts/` 目录，
提醒永久消失。不付也完全不影响使用。

## 授权

- 仓库完全公开，随便装、随便学；请勿去掉溯源水印冒充原创倒卖。
- 执行层依赖 Tencent BrowserSkill（MIT，见 NOTICE.md）。
