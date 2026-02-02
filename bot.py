#!/usr/bin/env python3
import os
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

OUT_FILE = os.environ.get("OUT_FILE", "/opt/telegram-inbox/inbox.md")
OUT_DIR = os.path.dirname(OUT_FILE)
OUT_BASE = os.path.splitext(os.path.basename(OUT_FILE))[0]

# 建议：先不填，跑起来后对 bot 发 /id 来获取自己的 user id，再填回去
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID", "")
ALLOWED_USER_ID = int(ALLOWED_USER_ID) if ALLOWED_USER_ID.strip() else None


def now_str() -> str:
    # 默认用服务器本地时区。你也可以在 systemd 里设置 TZ=Asia/Shanghai
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def header_time_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def month_file_path(dt: datetime) -> str:
    return os.path.join(OUT_DIR, f"{OUT_BASE}_{dt.year}.{dt.month}.md")


def find_last_header_time(file_path: str) -> datetime | None:
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None

    header_re = re.compile(r"^##\s*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]")
    for line in reversed(lines):
        match = header_re.match(line.strip())
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M").astimezone()
            except ValueError:
                return None
    return None


def should_start_new_header(now_dt: datetime, last_header: datetime | None) -> bool:
    if last_header is None:
        return True
    if now_dt.date() != last_header.date():
        return True
    return now_dt - last_header > timedelta(hours=12)


def build_write_block(now_dt: datetime, text: str, file_path: str) -> str:
    last_header = find_last_header_time(file_path)
    parts = []
    if should_start_new_header(now_dt, last_header):
        parts.append(f"\n## [{header_time_str(now_dt)}]\n")
    parts.append(f"- [{now_str()}] {text}\n")
    return "".join(parts)


def safe_inbox_path(arg: str | None, now_dt: datetime) -> str:
    if arg:
        name = os.path.basename(arg)
        return os.path.join(OUT_DIR, name)
    return month_file_path(now_dt)


def split_chunks(text: str, size: int = 3800) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id if update.effective_user else None
    await update.message.reply_text(f"your user_id = {uid}")


async def cmd_ls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not is_allowed(update):
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(
        [
            f
            for f in os.listdir(OUT_DIR)
            if f.startswith(f"{OUT_BASE}_") and f.endswith(".md")
        ]
    )
    if not files:
        await update.message.reply_text("(empty)")
        return
    await update.message.reply_text("\n".join(files))


async def cmd_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not is_allowed(update):
        return
    arg = context.args[0] if context.args else None
    file_path = safe_inbox_path(arg, datetime.now().astimezone())
    if not os.path.exists(file_path):
        await update.message.reply_text("文件不存在")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        await update.message.reply_text("(empty)")
        return
    for chunk in split_chunks(content):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not is_allowed(update):
        return
    arg = context.args[0] if context.args else None
    file_path = safe_inbox_path(arg, datetime.now().astimezone())
    if not os.path.exists(file_path):
        await update.message.reply_text("文件不存在")
        return
    await update.message.reply_document(
        document=open(file_path, "rb"), filename=os.path.basename(file_path)
    )


def is_allowed(update: Update) -> bool:
    if ALLOWED_USER_ID is None:
        return True  # 方便你第一次用 /id，之后务必改成只允许自己
    u = update.effective_user
    return bool(u and u.id == ALLOWED_USER_ID)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if not is_allowed(update):
        return

    text = update.message.text.replace("\n", " ").strip()
    now_dt = datetime.now().astimezone()
    file_path = month_file_path(now_dt)
    block = build_write_block(now_dt, text, file_path)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(block)

    await update.message.reply_text(f"✅ 已写入 {os.path.basename(file_path)}")


def main():
    token = os.environ["BOT_TOKEN"]  # 没设置就直接报错，避免默默失败
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("ls", cmd_ls))
    app.add_handler(CommandHandler("read", cmd_read))
    app.add_handler(CommandHandler("get", cmd_get))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()
