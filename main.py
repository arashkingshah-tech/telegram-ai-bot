import os
import logging
from typing import List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# ===== ENV NAMES (همون اسم‌های قبلی) =====
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")    # تو Render همین نام
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")    # تو Render همین نام
TARGET_CHANNEL_1 = os.getenv("TARGET_CHANNEL_1")  # -1001454872532
TARGET_CHANNEL_2 = os.getenv("TARGET_CHANNEL_2")  # -1003022912690
TARGET_CHANNEL_3 = os.getenv("TARGET_CHANNEL_3")  # -1003038687250

TARGET_CHANNELS: List[str] = [ch for ch in [TARGET_CHANNEL_1, TARGET_CHANNEL_2, TARGET_CHANNEL_3] if ch]

# ===== Checks =====
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN not set")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")

# ===== Logging =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("timewin-bot")

# ===== OpenAI client =====
client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ربات فعاله ✅\n"
        "برای ارسال به کانال‌ها: /post متن\n"
        "هر پیام معمولی هم پاسخ هوش مصنوعی می‌گیره.",
        parse_mode=ParseMode.HTML,
    )

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not TARGET_CHANNELS:
        await update.message.reply_text("کانال هدف تنظیم نشده است.")
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("استفاده: /post متنِ پست")
        return

    sent = 0
    for ch in TARGET_CHANNELS:
        try:
            await context.bot.send_message(chat_id=int(ch), text=text, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception as e:
            logger.exception(f"Failed to send to {ch}: {e}")
    await update.message.reply_text(f"انجام شد ✅ ({sent} کانال)")

def ai_answer(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Keep replies concise."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.exception(f"OpenAI error: {e}")
        return "متاسفم، سرویس هوش مصنوعی الان در دسترس نیست."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    reply = ai_answer(update.message.text.strip())
    await update.message.reply_text(reply)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Exception while handling an update:", exc_info=context.error)

def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("Bot is up and running …")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()