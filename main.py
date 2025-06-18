import os
import re
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

def extract_links(text):
    return re.findall(r'https?://\S+', text)

def detect_platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "facebook.com" in url:
        return "facebook"
    return "unknown"

def get_media_links_yt_dlp(url):
    ydl_opts = {
        'quiet': True,
        'format': 'best',
        'skip_download': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                return [entry['url'] for entry in info['entries']]
            return [info.get('url')]
    except Exception as e:
        logging.error(f"[yt_dlp ERROR] {e}")
        return []

def get_instagram_images(url):
    try:
        r = requests.post("https://saveig.app/api/ajaxSearch", data={"q": url}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return [m['url'] for m in data.get("medias", []) if "url" in m]
    except Exception as e:
        logging.error(f"[Instagram ERROR] {e}")
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a YouTube, Instagram, or Facebook link to get media.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = extract_links(update.message.text)
    if not links:
        await update.message.reply_text("❌ No links found.")
        return

    for url in links:
        platform = detect_platform(url)
        await update.message.reply_text(f"🔍 Fetching media from {platform}...")

        media_urls = []
        if platform in ["youtube", "facebook"]:
            media_urls = get_media_links_yt_dlp(url)
        elif platform == "instagram":
            media_urls = get_instagram_images(url)

        if not media_urls:
            fallback = f"https://www.hitube.io/en?url={url}"
            await update.message.reply_text(
    f"❌ Failed to fetch media from {platform.title()}.\n👉 Try manually:\n{fallback}"
)
            continue

        for media in media_urls:
            if media.endswith(".mp4") or "googlevideo" in media:
                await update.message.reply_text(f"🎥 Video:\n{media}")
            else:
                await update.message.reply_photo(media)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ Bot is running...")
    app.run_polling()
