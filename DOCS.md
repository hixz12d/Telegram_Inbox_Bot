# 官方使用说明

## 目的

把 Telegram 变成随手记录入口：发送文本消息给 bot，内容追加写入 Markdown 文件，方便后续整理。

## 前置条件

- Python 3.10+
- 已创建 Telegram Bot（拿到 Bot Token）
- 依赖：python-telegram-bot

## 安装

```bash
pip install python-telegram-bot
```

## 配置

环境变量：

- `BOT_TOKEN`（必填）：Telegram Bot Token
- `ALLOWED_USER_ID`（可选）：允许写入的 Telegram user_id
- `OUT_FILE`（可选）：输出路径，默认 `/opt/telegram-inbox/inbox.md`
- `TZ`（可选）：时区，例如 `Asia/Shanghai`

## 运行

```bash
python3 bot.py
```

## 命令

- `/id`：返回你的 Telegram user_id
- `/ls`：列出所有 `inbox_*.md`
- `/read`：读取最近月文件
- `/read inbox_2026.1.md`：读取指定文件
- `/get`：发送最近月文件（兼容 /get md）
- `/get inbox_2026.1.md`：发送指定文件（兼容旧用法）
- `/get md inbox_2026.1.md`：发送指定文件
- `/get media`：打包发送媒体文件
- `/remove media`：清空媒体文件（需 confirm）

## 媒体保存

- 图片保存到：`{OUT_DIR}/media/YYYY.M/`
- 文件名：`<file_unique_id>.jpg`
- md 记录格式示例：`- [2026-02-03 12:00:00 CST] [图片] media/2026.2/abcdef.jpg`

## 写入格式

- 文件名：`inbox_YYYY.M.md`
- 分组标题：`## [YYYY-MM-DD HH:MM]`
- 列表项：`- [YYYY-MM-DD HH:MM:SS TZ] 内容`

时间分组规则：同一天内 12 小时内的内容归到同一个时间戳标题下；跨天则新标题。

## 部署到 VPS（systemd）

示例服务文件：`/etc/systemd/system/telegram-inbox.service`

```ini
[Unit]
Description=Telegram Inbox Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/telegram-inbox
Environment=BOT_TOKEN=YOUR_BOT_TOKEN
Environment=ALLOWED_USER_ID=YOUR_USER_ID
Environment=OUT_FILE=/opt/telegram-inbox/inbox.md
Environment=TZ=Asia/Shanghai
ExecStart=/usr/bin/python3 /opt/telegram-inbox/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动/重启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-inbox.service
sudo systemctl restart telegram-inbox.service
```

查看状态与日志：

```bash
sudo systemctl status telegram-inbox.service --no-pager
sudo journalctl -u telegram-inbox.service -f
```

## 版本记录

- **v0.1**：基础写入 `inbox.md`、/id、白名单
- **v0.2**：按月分文件、12 小时内时间分组、/read /get /ls
- **v0.3**：支持图片保存、媒体打包导出与清理（/get media、/remove media）

## 常见问题

1) **/read 显示不完整**：消息过长会分段发送，属正常现象。
2) **无法导入 telegram**：确认已安装 `python-telegram-bot`。
3) **时区不正确**：设置系统时区或 `TZ=Asia/Shanghai`。

## 安全建议

- 配置 `ALLOWED_USER_ID`，避免他人写入。
- 不要在日志或文档中公开 `BOT_TOKEN`。
