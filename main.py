import os
import re
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")

def extract_links(text):
    return re.findall(r'https?://\\S+', text)

def detect_platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "facebook.com" in url:
        return "facebook"
    return "unknown"

def try_yt_dlp(url):
    try:
        ydl_opts = {
            'quiet': True,
            'format': 'best',
            'skip_download': True
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                return [entry['url'] for entry in info['entries']]
            return [info.get('url')]
    except Exception as e:
        logging.warning(f"[yt_dlp FAIL] {e}")
        return []

def try_saveig(url):
    try:
        r = requests.post("https://saveig.app/api/ajaxSearch", data={"q": url}, timeout=10)
        if r.ok:
            return [m['url'] for m in r.json().get("medias", []) if "url" in m]
    except Exception as e:
        logging.warning(f"[saveig FAIL] {e}")
    return []

def try_snapinsta(url):
    try:
        r = requests.post("https://snapinsta.app/api/ajaxSearch", data={"q": url}, timeout=10)
        if r.ok and 'url' in r.text:
            return [m['url'] for m in r.json().get("medias", []) if "url" in m]
    except Exception as e:
        logging.warning(f"[snapinsta FAIL] {e}")
    return []

def try_fdown(url):
    try:
        r = requests.get(f"https://fdown.net/download.php?URLz={url}", timeout=10)
        matches = re.findall(r'https:\\/\\/video[^"]+\\.mp4', r.text)
        return [m.replace("\\/", "/") for m in matches]
    except Exception as e:
        logging.warning(f"[fdown FAIL] {e}")
    return []

def download_instagram(url):
    return try_yt_dlp(url) or try_saveig(url) or try_snapinsta(url)

def download_facebook(url):
    return try_yt_dlp(url) or try_fdown(url)

def download_youtube(url):
    return try_yt_dlp(url)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send YouTube, Instagram, or Facebook link to download media.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = extract_links(update.message.text)
    for url in links:
        platform = detect_platform(url)
        await update.message.reply_text(f"🔍 Fetching media from {platform}...")
        media_urls = []

        if platform == "youtube":
            media_urls = download_youtube(url)
        elif platform == "instagram":
            media_urls = download_instagram(url)
        elif platform == "facebook":
            media_urls = download_facebook(url)

        if not media_urls:
            await update.message.reply_text(
                f"❌ Could not fetch media from {platform.title()}.\n"
                f"🔗 Try manually: https://www.hitube.io/en?url={url}"
            )
            continue

        for media in media_urls:
            try:
                if media.endswith(".mp4") or "googlevideo.com" in media:
                    await update.message.reply_video(media)
                else:
                    await update.message.reply_photo(media)
            except Exception as e:
                logging.warning(f"[SEND FAIL] {e}")
                await update.message.reply_text(f"⚠️ Failed to send media. Try downloading:\n{media}")

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("✅ Bot is running...")
    app.run_polling()
