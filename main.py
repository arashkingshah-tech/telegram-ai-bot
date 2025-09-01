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
logger = logging.getLogger("relay-bot")

# -------- ENV --------
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

# کانال سورس (فارسی) و مقصدها (انگلیسی/ترکی) - حتماً آیدی‌ عددی با -100 شروع
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
EN_CHANNEL_ID     = int(os.getenv("EN_CHANNEL_ID", "0"))
TR_CHANNEL_ID     = int(os.getenv("TR_CHANNEL_ID", "0"))

missing = []
if not TELEGRAM_TOKEN:    missing.append("TELEGRAM_TOKEN")
if not OPENAI_API_KEY:    missing.append("OPENAI_API_KEY")
if not SOURCE_CHANNEL_ID: missing.append("SOURCE_CHANNEL_ID")
if missing:
    raise RuntimeError(f"❌ ENV ناقصه: {', '.join(missing)} را تنظیم کنید.")

# -------- OpenAI (SDK جدید) --------
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's Persian text to {lang}.\n"
    "Keep the meaning natural and fluent. Preserve emojis, hashtags, URLs, and @usernames as-is.\n"
    "Do NOT add extra commentary. Return ONLY the translation."
)

async def translate(text: str, lang: str) -> str:
    """Translate Persian text to the given language using OpenAI."""
    if not text:
        return ""
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system","content": SYSTEM_PROMPT.format(lang=lang)},
                {"role":"user","content": text},
            ],
            temperature=0.2,
        )
        out = (resp.choices[0].message.content or "").strip()
        return out
    except Exception as e:
        logger.exception(f"OpenAI error: {e}")
        # در بدترین حالت همان متن اصلی را برگردان
        return text

# -------- Commands --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋 ربات انتقال/ترجمه فعاله. فقط داخل کانال فارسی پست بگذارید؛ "
        "به‌صورت خودکار به انگلیسی و ترکی در کانال‌های مقصد ارسال می‌شود."
    )

# -------- Channel posts handler (متن و مدیا) --------
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or msg.chat_id != SOURCE_CHANNEL_ID:
        return

    # 1) اگر پست متنی ساده بود
    if msg.text and not any([msg.photo, msg.video, msg.document, msg.animation, msg.audio, msg.voice, msg.sticker]):
        src_text = (msg.text or "").strip()
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
        return

    # 2) اگر پست مدیا بود (عکس/ویدیو/فایل/گیف/صوت...) با یا بدون کپشن
    has_media = any([msg.photo, msg.video, msg.document, msg.animation, msg.audio, msg.voice, msg.sticker])
    if has_media:
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

# -------- Error logger --------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # /start (اختیاری)
    app.add_handler(CommandHandler("start", start))

    # فقط پست‌های کانال (همه انواع؛ داخل تابع تشخیص می‌دهیم متن/مدیاست)
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))

    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()    
