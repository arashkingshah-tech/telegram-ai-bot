import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from openai import OpenAI

# -------- Logging --------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------- ENV --------
TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
SOURCE_CHANNEL_ID  = int(os.getenv("SOURCE_CHANNEL_ID", "0"))  # کانال فارسی
EN_CHANNEL_ID      = int(os.getenv("EN_CHANNEL_ID", "0"))      # کانال انگلیسی
TR_CHANNEL_ID      = int(os.getenv("TR_CHANNEL_ID", "0"))      # کانال ترکی

if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SOURCE_CHANNEL_ID:
    raise RuntimeError("❌ ENV ناقصه: TELEGRAM_TOKEN, OPENAI_API_KEY, SOURCE_CHANNEL_ID رو تنظیم کنید.")

# OpenAI client (نسخه جدید SDK)
client = OpenAI(api_key=OPENAI_API_KEY)   # ⚠️ بدون proxies

# -------- Helpers --------
SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's Persian text to {lang}.\n"
    "Keep meaning natural and fluent. Preserve emojis, hashtags, URLs and usernames as-is.\n"
    "Do NOT add extra commentary. Return ONLY the translation."
)

async def translate(text: str, lang: str) -> str:
    if not text:
        return ""
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(lang=lang)},
                {"role": "user", "content": text}
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.exception(f"OpenAI error: {e}")
        return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 ربات ترجمهٔ کانال فعاله. فقط توی کانال فارسی پست بزار 👌")

# -------- Handlers --------

# پست‌های متنی
async def handle_channel_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or msg.chat_id != SOURCE_CHANNEL_ID:
        return
    src_text = (msg.text or msg.caption or "").strip()
    if not src_text:
        return

    logger.info("New TEXT post from source")
    en_text = await translate(src_text, "English")
    tr_text = await translate(src_text, "Turkish")

    try:
        if EN_CHANNEL_ID and en_text:
            await context.bot.send_message(chat_id=EN_CHANNEL_ID, text=en_text)
        if TR_CHANNEL_ID and tr_text:
            await context.bot.send_message(chat_id=TR_CHANNEL_ID, text=tr_text)
    except Exception as e:
        logger.exception(f"send text error: {e}")

# پست‌های رسانه‌ای
async def handle_channel_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or msg.chat_id != SOURCE_CHANNEL_ID:
        return

    has_media = any([msg.photo, msg.video, msg.document, msg.audio, msg.voice])
    if not has_media:
        return

    caption = (msg.caption or "").strip()
    logger.info("New MEDIA post from source")

    en_cap = await translate(caption, "English") if caption else ""
    tr_cap = await translate(caption, "Turkish") if caption else ""

    try:
        if EN_CHANNEL_ID:
            await context.bot.copy_message(
                chat_id=EN_CHANNEL_ID,
                from_chat_id=SOURCE_CHANNEL_ID,
                message_id=msg.message_id,
                caption=en_cap or caption or None
            )
        if TR_CHANNEL_ID:
            await context.bot.copy_message(
                chat_id=TR_CHANNEL_ID,
                from_chat_id=SOURCE_CHANNEL_ID,
                message_id=msg.message_id,
                caption=tr_cap or caption or None
            )
    except Exception as e:
        logger.exception(f"copy media error: {e}")

# خطاها
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.TEXT, handle_channel_text))
    media_filter = (
        filters.ChatType.CHANNEL &
        (filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.VOICE)
    )
    app.add_handler(MessageHandler(media_filter, handle_channel_media))

    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
