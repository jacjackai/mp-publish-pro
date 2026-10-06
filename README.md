# mp-publish-pro · 公众号自动发布技能

让 AI 编码 agent（Claude Code / OpenCode / Codex / Cursor 等）驱动 Chrome，完成微信公众号文章的
建草稿、配图、封面裁剪、发表前置设置直至扫码发表的全流程自动化。

本体是一份 Agent Skills 标准格式的 `SKILL.md`（操作剧本）+ 辅助脚本，执行层依赖开源的
[Tencent BrowserSkill](https://github.com/Tencent/BrowserSkill)（MIT，见 `NOTICE.md`）。

## 安装（两条命令）

**① 环境体检**：装 bsk CLI（钉在实测版本 0.3.2）、查 Chrome、引导装扩展、`bsk doctor` 全绿当闸。可重复跑，装不上就带着脚本输出提 issue：

```bash
curl -fsSL https://raw.githubusercontent.com/jacjackai/mp-publish-pro/main/setup.sh | sh
```

不想 `curl | sh`：clone 本仓库后跑 `sh setup.sh`，效果相同。

**② 装技能本体**：安装器自动探测本机 agent 并放到正确目录；更新重跑同一条命令即可。

```bash
npx skills add jacjackai/mp-publish-pro --skill wechat-mp-publish
```

### 手动装环境（setup.sh 做的事，供对照/排障）

1. **bsk** CLI：`curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | BSK_VERSION=0.3.2 sh`，`bsk doctor` 全绿再开工。**禁止 `bsk update --yes`**（0.3.x 为实测线，升级走 headless 冒烟 + doctor 全绿）
2. **Chrome + BrowserSkill 扩展**：[Chrome 商店直达](https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi)，装好打开扩展弹窗启用本地连接，`bsk browsers` 能看到浏览器
3. **公众号登录态**：`bsk navigate "https://mp.weixin.qq.com/"` 后落扫码页即需人工扫码一次，登录态随后按 Chrome profile 持久
4. **用户配置**：复制 `skills/wechat-mp-publish/user.conf.example` 为同目录 `user.conf` 并填写（原创作者名必填；合集、赞赏账户可留空跳过）

### 不加载技能格式的 agent（如 Qoder）

```bash
git clone https://github.com/jacjackai/mp-publish-pro.git
```

把 `skills/wechat-mp-publish/` 整个目录拷到 agent 的技能目录
（Claude Code：`~/.claude/skills/`；OpenCode：`~/.config/opencode/skills/`，其余同理），
或在首次对话里直接要求：

> 发公众号前，先完整阅读 skills/wechat-mp-publish/SKILL.md 并严格按它执行。

## 使用

对 agent 说「发公众号 / 把这篇发到公众号 / 更新公众号」即可触发；会话结束时 agent 应执行
`bsk session stop` 收尾。发表环节的微信扫码必须由账号本人完成，技能会在扫码浮层处停下等待。

## 收费方式：请喝咖啡

全功能、永久免费、没有任何锁——每次发表全流程都能跑。

如果它确实替你省了工夫，可以 9.9 元请作者喝杯咖啡：用满 3 次后会不定期提醒
（首次必提，之后大约每 2~5 次出现一次，含微信二维码，agent 会展示给你）。
**付过的人作者会回发一个 `license.key`**，放进 `skills/wechat-mp-publish/scripts/` 目录，
提醒永久消失。不付也完全不影响使用。

## 交流 / 支持

- **微信扫码**（进交流群 · 提需求 · 请咖啡，一个码全包）：<https://jacjackai.github.io/mp-publish-pro/join/>——页面地址永不改变，换码只换图，建议收藏
- 装不上、有 bug：带着 `setup.sh` 的输出去 [GitHub Issues](https://github.com/jacjackai/mp-publish-pro/issues)

## 授权

- 仓库完全公开，随便装、随便学；请勿去掉溯源水印冒充原创倒卖。
- 执行层依赖 Tencent BrowserSkill（MIT，见 NOTICE.md）。
