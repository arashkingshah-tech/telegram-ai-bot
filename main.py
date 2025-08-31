import os
import logging
import filetype
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# گرفتن توکن‌ها از محیط
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# فعال‌سازی لاگ برای دیباگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من بات هوش مصنوعی تایم‌وین هستم. هر سوالی داری بپرس!")

# هندل پیام‌های متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_message}],
        )

        ai_text = response.choices[0].message.content
        await update.message.reply_text(ai_text)

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("یه مشکلی پیش اومده، دوباره تلاش کن ✨")

# هندل فایل‌ها (اختیاری – اگر بخوای کار کنه)
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "temp_file"
    await file.download_to_drive(file_path)

    kind = filetype.guess(file_path)
    if kind:
        await update.message.reply_text(f"نوع فایل شناسایی شد: {kind.mime}")
    else:
        await update.message.reply_text("نتونستم نوع فایل رو تشخیص بدم ❌")

# اجرای اصلی
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
