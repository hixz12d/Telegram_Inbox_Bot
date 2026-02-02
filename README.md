# Telegram Inbox Bot（Markdown 收件箱）

把 Telegram 变成「随手记录入口」：给 bot 发送文本消息，它会追加写入 Markdown 文件，方便后续整理。

👉 详细使用文档请看：[DOCS.md](./DOCS.md)

## 功能特性（v0.2）

- 按月分文件：`inbox_YYYY.M.md`
- 同日 12 小时内归为同一时间戳分组
- 命令支持：/id、/ls、/read、/get
- 白名单：仅允许指定 user_id 写入

## 快速开始

```bash
pip install python-telegram-bot
python3 bot.py
```

## 环境变量

- `BOT_TOKEN`（必填）
- `ALLOWED_USER_ID`（可选）
- `OUT_FILE`（可选，默认 `/opt/telegram-inbox/inbox.md`）
- `TZ`（可选）

## 命令速查

- `/id`：返回你的 Telegram user_id
- `/ls`：列出所有 `inbox_*.md`
- `/read`：读取最近月文件
- `/get`：发送最近月文件

## 版本记录

- **v0.1**：基础写入 `inbox.md`、/id、白名单
- **v0.2**：按月分文件、12 小时内时间分组、/read /get /ls

## 边界说明

- 仅处理文本消息；语音、图片、文件等暂不写入
- 不做自动整理、标签、摘要、分类、搜索等高级能力
