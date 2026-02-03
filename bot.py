#!/usr/bin/env python3
import os
import re
import shutil
import zipfile
from datetime import datetime, timedelta
from telegram import Update
from telegram.error import TelegramError


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
MEDIA_DIR = os.path.join(OUT_DIR, "media")


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


def safe_media_name(arg: str) -> str:
    return os.path.basename(arg)


def month_media_dir(now_dt: datetime) -> str:
    return os.path.join(MEDIA_DIR, f"{now_dt.year}.{now_dt.month}")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def default_photo_name(now_dt: datetime, ext: str) -> str:
    safe_ext = ext if ext.startswith(".") else f".{ext}" if ext else ""
    return f"photo_{now_dt.strftime('%Y%m%d_%H%M%S')}{safe_ext}"


def build_media_write_block(now_dt: datetime, text: str, file_path: str) -> str:
    last_header = find_last_header_time(file_path)
    parts = []
    if should_start_new_header(now_dt, last_header):
        parts.append(f"\n## [{header_time_str(now_dt)}]\n")
    parts.append(f"- [{now_str()}] {text}\n")
    return "".join(parts)


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

    arg = context.args[0].lower() if context.args else ""
    now_dt = datetime.now().astimezone()

    if arg in ("media", "media.zip"):
        await send_media_zip(update, now_dt)
        return

    if arg in ("", "md"):
        if len(context.args) > 1:
            file_name = safe_media_name(context.args[1])
            file_path = os.path.join(OUT_DIR, file_name)
        else:
            file_path = safe_inbox_path(None, now_dt)
    else:
        file_path = safe_inbox_path(arg, now_dt)

    if not os.path.exists(file_path):
        await update.message.reply_text("文件不存在")
        return

    await update.message.reply_document(
        document=open(file_path, "rb"), filename=os.path.basename(file_path)
    )


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not is_allowed(update):
        return

    arg = context.args[0].lower() if context.args else ""
    if arg != "media":
        await update.message.reply_text("用法：/remove media [confirm]")
        return

    confirm = len(context.args) > 1 and context.args[1].lower() == "confirm"
    if not confirm:
        await update.message.reply_text("确认清空媒体文件？发送：/remove media confirm")
        return

    try:
        if os.path.exists(MEDIA_DIR):
            shutil.rmtree(MEDIA_DIR)
        await update.message.reply_text("✅ 媒体文件已清空")
    except OSError:
        await update.message.reply_text("清空失败，请检查权限")


async def send_media_zip(update: Update, now_dt: datetime) -> None:
    if not update.message:
        return

    if not os.path.exists(MEDIA_DIR):
        await update.message.reply_text("媒体目录为空")
        return

    zip_dir = os.path.join(OUT_DIR, "tmp")
    ensure_dir(zip_dir)
    zip_name = f"media_{now_dt.year}.{now_dt.month}.zip"
    zip_path = os.path.join(zip_dir, zip_name)

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(MEDIA_DIR):
                for file_name in files:
                    abs_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(abs_path, MEDIA_DIR)
                    zf.write(abs_path, rel_path)
        await update.message.reply_document(
            document=open(zip_path, "rb"), filename=zip_name
        )
    except OSError:
        await update.message.reply_text("打包失败，请检查磁盘权限")
    finally:
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except OSError:
            pass


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

    ensure_dir(OUT_DIR)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(block)

    await update.message.reply_text(f"✅ 已写入 {os.path.basename(file_path)}")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    if not is_allowed(update):
        return

    now_dt = datetime.now().astimezone()
    photo = update.message.photo[-1]
    caption = (update.message.caption or "").replace("\n", " ").strip()

    ext = ".jpg"
    if photo.file_unique_id:
        base_name = photo.file_unique_id
    else:
        base_name = default_photo_name(now_dt, ext)
    file_name = f"{base_name}{ext}" if not base_name.endswith(ext) else base_name

    target_dir = month_media_dir(now_dt)
    ensure_dir(target_dir)
    file_path = os.path.join(target_dir, file_name)

    try:
        file_obj = await photo.get_file()
        await file_obj.download_to_drive(file_path)
    except TelegramError:
        await update.message.reply_text("图片保存失败，请稍后再试")
        return
    except OSError:
        await update.message.reply_text("图片保存失败，请检查磁盘权限")
        return

    md_path = month_file_path(now_dt)
    rel_path = os.path.relpath(file_path, OUT_DIR)
    note = f"[图片] {rel_path}"
    if caption:
        note = f"[图片] {caption} ({rel_path})"

    block = build_media_write_block(now_dt, note, md_path)
    with open(md_path, "a", encoding="utf-8") as f:
        f.write(block)

    await update.message.reply_text(f"✅ 已保存图片 {os.path.basename(file_path)}")


def main():
    token = os.environ["BOT_TOKEN"]  # 没设置就直接报错，避免默默失败
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("ls", cmd_ls))
    app.add_handler(CommandHandler("read", cmd_read))
    app.add_handler(CommandHandler("get", cmd_get))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()
