import os
import logging
import filetype
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# فعال‌کردن لاگ برای اشکال‌زدایی
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# گرفتن توکن‌ها از متغیرهای محیطی
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من بات تایم‌وین هستم! هر چی بپرسی جواب میدم ✅")

# هندل پیام‌های متنی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI bot."},
                {"role": "user", "content": user_message}
            ]
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        logger.error(f"خطا در OpenAI: {e}")
        await update.message.reply_text("متاسفم 😔 خطایی رخ داد.")

# هندل فایل‌ها (برای تشخیص نوع فایل با filetype)
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "temp_file"

    await file.download_to_drive(file_path)

    kind = filetype.guess(file_path)
    if kind is not None:
        file_type = kind.mime
    else:
        file_type = "unknown"

    await update.message.reply_text(f"📂 فایل شما از نوع: {file_type}")

    os.remove(file_path)

# شروع ربات
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    application.run_polling()

if __name__ == "__main__":
    main()
