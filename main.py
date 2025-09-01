import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import openai

# ===== لاگ =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== ENV =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID"))   # کانال فارسی
EN_CHANNEL_ID = int(os.getenv("EN_CHANNEL_ID"))           # کانال انگلیسی
TR_CHANNEL_ID = int(os.getenv("TR_CHANNEL_ID"))           # کانال ترکی

openai.api_key = OPENAI_API_KEY

# ===== ترجمه =====
async def translate_text(text: str, target_lang: str) -> str:
    """
    target_lang: 'English' یا 'Turkish'
    """
    try:
        resp = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following Persian text into {target_lang}. Only return the translation."},
                {"role": "user", "content": text}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 من ربات تایم‌وین هستم. پست‌ها رو برات ترجمه می‌کنم 🌍")

# ===== هندل پست‌های کانال فارسی =====
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if msg.chat.id != SOURCE_CHANNEL_ID:
        return

    original_text = msg.text or msg.caption

    en_text, tr_text = None, None
    if original_text:
        en_text = await translate_text(original_text, "English")
        tr_text = await translate_text(original_text, "Turkish")

    try:
        if msg.photo:  # پست تصویری
            # انگلیسی
            await context.bot.copy_message(
                chat_id=EN_CHANNEL_ID,
                from_chat_id=SOURCE_CHANNEL_ID,
                message_id=msg.message_id,
                caption=en_text if en_text else msg.caption
            )
            # ترکی
            await context.bot.copy_message(
                chat_id=TR_CHANNEL_ID,
                from_chat_id=SOURCE_CHANNEL_ID,
                message_id=msg.message_id,
                caption=tr_text if tr_text else msg.caption
            )
        elif msg.text:  # پست متنی
            if en_text:
                await context.bot.send_message(chat_id=EN_CHANNEL_ID, text=en_text)
            if tr_text:
                await context.bot.send_message(chat_id=TR_CHANNEL_ID, text=tr_text)
    except Exception as e:
        logger.error(f"Forward/send error: {e}")

# ===== main =====
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))

    app.run_polling()

if __name__ == "__main__":
    main()
