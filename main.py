import os
import logging
import filetype

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
import openai

# لاگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن‌ها از متغیر محیطی
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! بات وصل شد ✅")

# پیام متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text or ""
    try:
        resp = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message},
            ],
        )
        reply = resp.choices[0].message.content.strip()
        await update.message.reply_text(reply)
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("یه خطایی رخ داد. بعداً دوباره تلاش کن.")

# عکس/فایل تصویری (اختیاری)
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # اگر فعلاً لازم نداری می‌تونی این هندلر رو حذف کنی
    await update.message.reply_text("عکس دریافت شد ✅")

# خطاهای کلی
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Exception while handling an update:", exc_info=context.error)

def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است")
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY تنظیم نشده است")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    app.add_error_handler(error_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
