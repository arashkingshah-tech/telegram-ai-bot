import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("relay-bot")

# ---------- ENV ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# کانال مبدا (فارسی) و مقصدها (انگلیسی/ترکی) - حتماً با -100 شروع می‌شن
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0"))
EN_CHANNEL_ID     = int(os.getenv("EN_CHANNEL_ID", "0"))
TR_CHANNEL_ID     = int(os.getenv("TR_CHANNEL_ID", "0"))

if not (TELEGRAM_TOKEN and OPENAI_API_KEY and SOURCE_CHANNEL_ID):
    raise RuntimeError("ENV ناقصه: TELEGRAM_TOKEN, OPENAI_API_KEY, SOURCE_CHANNEL_ID را تنظیم کنید.")

# OpenAI SDK جدید – بدون پارامتر proxies
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a professional translator. Translate the user's Persian text to {lang}."
    " Keep it natural and fluent. Preserve emojis, hashtags, URLs and usernames exactly."
    " Do NOT add extra commentary. Return ONLY the translation."
)

async def translate(text: str, lang: str) -> str:
    """ترجمه با دمای کم برای خروجی روان و دقیق"""
    if not text:
        return ""
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(lang=lang)},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.exception(f"OpenAI error: {e}")
        # اگر خطا بود، همون متن اصلی رو برمی‌گردونیم تا پست از بین نره
        return text

# ---------- Commands ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات رله/ترجمه فعاله. فقط توی کانال مبدا پست بگذارید.")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

# ---------- Handlers ----------
def _is_media(msg) -> bool:
    return any([msg.photo, msg.video, msg.document, msg.animation, msg.audio, msg.voice, msg.sticker])

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هر پست جدید در کانال مبدا را می‌گیرد، ترجمه می‌کند و به مقصدها می‌فرستد."""
    msg = update.channel_post
    if not msg or msg.chat_id != SOURCE_CHANNEL_ID:
        return

    caption_or_text = (msg.text or msg.caption or "").strip()
    en_text = await translate(caption_or_text, "English") if caption_or_text else ""
    tr_text = await translate(caption_or_text, "Turkish") if caption_or_text else ""

    try:
        if _is_media(msg):
            # رسانه را عیناً کپی می‌کنیم و فقط کپشن را جایگزین می‌کنیم
            if EN_CHANNEL_ID:
                await context.bot.copy_message(
                    chat_id=EN_CHANNEL_ID,
                    from_chat_id=SOURCE_CHANNEL_ID,
                    message_id=msg.message_id,
                    caption=en_text or caption_or_text or None,
                )
            if TR_CHANNEL_ID:
                await context.bot.copy_message(
                    chat_id=TR_CHANNEL_ID,
                    from_chat_id=SOURCE_CHANNEL_ID,
                    message_id=msg.message_id,
                    caption=tr_text or caption_or_text or None,
                )
        else:
            # پستِ صرفاً متنی
            if EN_CHANNEL_ID and (en_text or caption_or_text):
                await context.bot.send_message(chat_id=EN_CHANNEL_ID, text=en_text or caption_or_text)
            if TR_CHANNEL_ID and (tr_text or caption_or_text):
                await context.bot.send_message(chat_id=TR_CHANNEL_ID, text=tr_text or caption_or_text)
        logger.info("Post relayed.")
    except Exception as e:
        logger.exception(f"Send/copy error: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception", exc_info=context.error)

# ---------- App ----------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ping",  ping_cmd))

    # فقط پست‌های کانالی مبدا؛ یک هندلر برای همه‌ی انواع پست کافیست
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))

    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
