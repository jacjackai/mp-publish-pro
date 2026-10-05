---
name: wechat-mp-publish
description: 公众号文章发布自动化 — bsk（BrowserSkill）驱动 mp.weixin.qq.com 编辑器：建草稿（标题/正文/配图/封面/摘要）直至扫码发表。图片库选图、裁剪封面、发表确认链全流程。v2.0 起执行层为 bsk 原生输入（原 CDP 版选择器知识保留复用）。触发 /mp-publish，或要求"发公众号/把文章发到公众号/更新公众号"时使用
version: 2.0.0
trigger: /mp-publish
tags: [wechat, mp, 公众号, publish, bsk]
---

# wechat-mp-publish — 公众号文章发布自动化（bsk 路线）

**v2.0（2026-09-20）**：执行层从裸 CDP 迁到 bsk（CLI → daemon → 扩展 → Agent Window 借窗）。
**关键迁移结论：bsk 点击是扩展原生的真实输入，原 CDP 版"必须 computer-use 真点"的
图片库选图、封面裁剪确认等步骤，bsk click 全部直接通过**（2026-09-20 全链实测：选图卡片 selected、
crop_multi POST 200、cover 落库）。原 CDP 脚本（scripts/）保留作备用参考，不再为主通路。

## 0. 纪律与红线

- **开工第一步：license 校验**。`python3 scripts/license_check.py`，退出码 1（无效）→ 停下告知用户；退出码 2（更新期已过）→ 可继续当前任务但提醒续费。

- **bsk pin 0.3.0，禁止 `bsk update --yes`**；升级走 headless 冒烟 + `bsk doctor` 全绿。
- 动浏览器前 `bsk browsers`；多实例时 `session start` 必带 `--browser <id> --no-focus`（默认不抢桌面焦点）；收尾必须 `bsk session stop <id>`。
- **真发表（扫码）是白名单动作**：发表确认链走到扫码即停，等用户手机扫码；其余草稿操作可自决。
- 每次点击/填充前取**最新 snapshot** 的 @eN 引用，跨快照引用一律作废重取。

## 0.5 用户配置（user.conf）

个人参数一律从本技能目录的 `user.conf` 读取（首次使用前复制 `user.conf.example` 生成），**不要硬编码**：

- `author`：原创声明作者名（≤8 字，必填）
- `collection`：默认合集名（可留空跳过）
- `reward_account`：赞赏账户名（可留空跳过）

## 1. 会话 + 登录态 + token

```bash
bsk browsers
bsk session start --browser <id> --no-focus --json     # session id 在顶层 session_id 字段
bsk navigate "https://mp.weixin.qq.com/" --session <sid>
```

- 登录态按 Chrome profile 持久；直接落 `/cgi-bin/home` 即在线。
- **token 从首页 URL 提取**（`token=NNNN`），每次登录会变。
- 落到扫码页 = 登录态失效 → 等用户扫码（登录态敏感，不自动化）。
- 落点 URL 可直接 navigate：
  - 编辑器：`/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&token={TOKEN}&lang=zh_CN`
  - 已有草稿：同上去掉 isNew，加 `&appmsgid={ID}`
  - 草稿箱：`/cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token={TOKEN}&lang=zh_CN`

## 2. 标题（⚠️ 与 CDP 版不同，2026-09-20 实测坑）

- **`#title` textarea 不可 focus**，`bsk fill --selector "#title"` 报 `Element is not focusable`。
- **CDP 版的 `#title.value` setter + input 事件会落「未命名」**（镜像不同步，实测保存后列表显示未命名）。
- **正确通路**：`execCommand('insertText')` 写标题镜像，计数器与 `#title` 双同步：

```js
// bsk evaluate
var t = document.querySelectorAll('.ProseMirror')[0];   // eds[0] = 标题镜像（title-editor__input 内）
t.focus();
document.execCommand('insertText', false, '文章标题');
// 验证：snapshot 计数器变 N/64；list_ex 的 title 字段（保存后延迟数秒可见）
```

- `bsk fill` 对标题 ProseMirror 会报 "fill target changed or lost focus before typing"，别用。
- 标题 ≤64 字。

## 3. 正文

两条通路都实测有效（2026-09-20）：

1. **纯文本（最简）**：snapshot 找正文框（placeholder「从这里开始写正文」@ref），
   `bsk click` 后 `bsk fill --value` 直写，`\n\n` 换行保留。
2. **富文本 HTML**：`bsk evaluate` 派发合成粘贴（与 CDP 版同手法，**同步写法，不要包 Promise**——
   bsk evaluate 不等待 Promise）：

```js
var eds=[...document.querySelectorAll('.ProseMirror')];
var body=eds.find(e=>(e.parentElement?.className||'').includes('rich_media_content'))||eds[1];
body.focus();
var dt=new DataTransfer();
dt.setData('text/html','<p>…</p>');     // 先简化为 <p>/<strong>，<img> 记位置后补
body.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));
```

- 仍遵守铁律：两个 `.ProseMirror`，正文是 `parent含rich_media_content` 的那个；
  `<img>/<blockquote>/<h2-h4>` 会被 schema 丢弃，先简化再粘，图片后补。
- 图片插入后光标停在图片处，先 Right 再粘下一段。

### 3.1 保存

- `Cmd+S` 无效。点右下角 **「保存为草稿」** button（snapshot 有 @ref）。
- **封面只在「保存为草稿」之后才落库**。

## 4. 配图与封面（bsk click 全通过，不再需要截图真点）

### 4.1 上传素材库

仍走 API：编辑器页 `bsk evaluate` 取 `window.wx.commonData.data` 的 uin/ticket/t，
或复用原 `scripts/mp_upload.py` 逻辑；scene=8 = 文章配图。

### 4.2 选图 + 封面裁剪（bsk 原生点击，实测通过）

1. 图片库对话框（正文「从图片库选择」或封面槽进入）：卡片选择器 `.weui-desktop-img-picker__item`，
   `bsk click --selector` 点第一个即中，**选中判据 = class 变 `... selected`**（evaluate 查）。
2. 点「下一步」→「编辑封面」裁剪页（2.35:1 + 1:1）→ 点「确认」。
   **判据：`bsk network` 里出现 `POST /cgi-bin/cropimage?action=crop_multi` 200**。
3. 点一次「保存为草稿」→ 延迟数秒后 `list_ex` 的 `cover` 出 mmbiz.qlogo.cn 即成功。
- 封面槽选择器仍有效：`#js_cover_area .js_cover_btn_area` → 菜单 `#js_cover_null` → `.js_imagedialog`。
- **API 查询有秒级延迟**：保存后立刻查为空，等 2-5 秒重查再下结论（标题字段同理）。

## 5. 发表前置四项设置（顺序有依赖，必做）

设置区在编辑器右侧，点具体可点元素（点整行常无效）：

| 顺序 | 项目 | 点哪里 | 要点 |
|---|---|---|---|
| 1 | 原创声明 | `.js_unset_original_title` | 类型=文字原创；作者必填 ≤8 字（从 user.conf 的 author 读取）；勾协议→确定 |
| 2 | 赞赏 | 赞赏行 `.js_reward_open`（须先原创） | 类型=赞赏作者；账户点「最近使用」内层 div；勾协议→确定 |
| 3 | 合集 | `.js_article_tags_label` | 下拉里**必须点中列表项 `li.select-opt-li`**，只打字不选=白干 |
| 4 | 创作来源 | `.js_claim_source_desc` | 选 **个人观点，仅供参考**（value=4）→ 确定 |

做完 → 「保存为草稿」→ `list_ex` 抽查 `cover / appmsg_album_infos / copyright_type=1`。

踩坑沿袭：原创作者框被占位标签盖住（focus 后走键盘）；浮层点确定后可能不自动关（右上角 X）；
**「一键排版」永远不要点**。

## 6. 发表确认链

1. 点「发表」→ 群发通知浮层 → 点浮层内「发表」→「继续发表」→
2. **微信扫码浮层 = 硬门，停在这里等用户手机扫码**；扫码阶段不动 Chrome 窗口。
3. 完成后跳 `/cgi-bin/home`，发表记录先「审核中」后「已发表」。

状态验证（双层 JSON，`publish_page`/`publish_info` 都是字符串）：

```
/cgi-bin/appmsgpublish?sub=list&begin=0&count=10&token=…&f=json&ajax=1
msg_status 102=审核中；appmsg_info[].content_url=文章链接
```

## 7. 收尾与清理

- 草稿箱删除测试草稿：草稿箱列表 → 卡片操作 link（hover 后出现）→ 弹窗「确定删除？…」→ 点「删除」button。
- 发表后内容不可改（masssendmodify 是纯预览），修排版唯一路径=删除重发（沿袭）。
- 排版规范沿袭：少表格多列表；代码块走工具栏「插入代码」+ 纯文本粘贴
  （原 §9 全部有效：视口宽度、「更多」下拉里同名按钮无效、伪块直接子元素选择器等坑照旧）。

## 8. 验收清单

- [ ] 标题在草稿列表显示真名（非「未命名」）
- [ ] 正文段落/加粗渲染正确（预览链接抽查）
- [ ] 图片全部 mmbiz.qpic.cn，无空占位
- [ ] 封面：`list_ex.cover` 非空
- [ ] 发表前置四项齐全（§5）
- [ ] 发表：扫码由用户完成；之后合集（user.conf 的 collection）+赞赏码开启
- [ ] `bsk session stop <sid>`

## 9. CDP 遗产（备用）

`scripts/`（mp_draft/mp_upload/mp_cover/mp_code/mp_del_by_id/raw_cdp.py）保留可跑，
页面级 CDP 直连方法不变（握手禁带 Origin）。注意：专用场景实例 `wechat-mp`(:9227) 的登录态
已于 2026-09-20 检查时失效，重启用需人工扫码；bsk 侧浏览器登录态有效（当日实测）。

## 10. 版本与真源

- **真源 = 主干** `~/myProject/WeChat/wechat-mp-publish/`（含 scripts/ 遗产），
  安装位 `~/.agents/skills/wechat-mp-publish/` 是产物。只改主干，再跑主干 `install.sh` 推送，
  禁止直接改安装位——2026-10 收编前本技能只有安装位副本，一次重装/同步就会丢改动。
- v2.0.0（执行层换 bsk 原生输入，CDP 知识降为 §9 备用）；2026-10-03 收编入主干。
