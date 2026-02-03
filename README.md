# Telegram Inbox Bot（Markdown 收件箱）

把 Telegram 变成「随手记录入口」：给 bot 发送文本消息，它会追加写入 Markdown 文件，方便后续整理。

👉 详细使用文档请看：[DOCS.md](./DOCS.md)

## 功能特性（v0.3）

- 按月分文件：`inbox_YYYY.M.md`
- 同日 12 小时内归为同一时间戳分组
- 命令支持：/id、/ls、/read、/get、/remove
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
- `/get`：发送最近月文件（兼容 /get md）
- `/get inbox_2026.1.md`：发送指定文件（兼容旧用法）
- `/get md inbox_2026.1.md`：发送指定文件
- `/get media`：打包发送媒体文件
- `/remove media`：清空媒体文件（需 confirm）

## 版本记录

- **v0.1**：基础写入 `inbox.md`、/id、白名单
- **v0.2**：按月分文件、12 小时内时间分组、/read /get /ls
- **v0.3**：支持图片保存、媒体打包导出与清理（/get media、/remove media）

## 边界说明

- 支持图片消息保存到 media，并在 md 中记录
- 语音、视频、文件等暂不处理
- 不做自动整理、标签、摘要、分类、搜索等高级能力
