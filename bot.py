import os
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import yt_dlp
import asyncio

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

# Pobieramy automatycznie główny adres z Rendera
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')

KANALY_YT = [
    'https://www.youtube.com/@giga.shoty67/shorts',
    'https://www.youtube.com/@tfardyyy/shorts',
    'https://www.youtube.com/@Menel_CS/shorts',
    'https://www.youtube.com/@alphajestem/shorts',
    'https://www.youtube.com/@CEESOWESHOTY/shorts'
]

LAST_SEEN_FILE = 'last_seen.json'

def load_last_seen():
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_last_seen(data):
    with open(LAST_SEEN_FILE, 'w') as f:
        json.dump(data, f)

# Inicjalizacja bota Telegrama
application = Application.builder().token(BOT_TOKEN).build()

async def check_and_send_shorts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Sprawdzam nowe Shortsy na wybranych kanałach...")
    
    last_seen = load_last_seen()
    ydl_opts = {'extract_flat': True, 'playlistend': 5, 'quiet': True}
    nowe_filmy_znalezione = False

    for kanal_url in KANALY_YT:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(kanal_url, download=False)
                if 'entries' not in info:
                    continue
                
                entries = info['entries']
                ostatni_zapisany_id = last_seen.get(kanal_url)
                
                nowe_entries = []
                for entry in entries:
                    if entry['id'] == ostatni_zapisany_id:
                        break
                    nowe_entries.append(entry)
                
                if entries:
                    last_seen[kanal_url] = entries[0]['id']

                for entry in reversed(nowe_entries):
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    await update.message.reply_text(f"⬇️ Pobieram nowy Short: {entry.get('title', 'Short')}")
                    
                    download_opts = {
                        'format': 'mp4[height<=1080]',
                        'outtmpl': 'temp_short.mp4',
                        'overwrites': True,
                        'quiet': True,
                    }
                    
                    with yt_dlp.YoutubeDL(download_opts) as ydl_down:
                        ydl_down.download([video_url])
                    
                    if os.path.exists('temp_short.mp4'):
                        with open('temp_short.mp4', 'rb') as video_file:
                            await context.bot.send_video(
                                chat_id=update.effective_chat.id,
                                video=video_file,
                                caption=f"🎬 **{entry.get('title')}**\n🔗 {video_url}"
                            )
                        os.remove('temp_short.mp4')
                        nowe_filmy_znalezione = True

            except Exception as e:
                await update.message.reply_text(f"Błąd przy sprawdzaniu kanału: {str(e)}")

    save_last_seen(last_seen)
    
    if not nowe_filmy_znalezione:
        await update.message.reply_text("✨ Brak nových Shortsów od ostatniego sprawdzania!")
    else:
        await update.message.reply_text("✅ Wszystkie nowe Shortsy zostały wysłane!")

application.add_handler(CommandHandler("start", check_and_send_shorts))
application.add_handler(CommandHandler("sprawdz", check_and_send_shorts))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Odbiera powiadomienia od Telegrama"""
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

@app.route("/")
def index():
    return "Bot Telegrama działa poprawnie przez Webhook!"

if __name__ == "__main__":
    # Automatyczne ustawienie webhooka w Telegramie przy starcie
    async def setup_webhook():
        await application.initialize()
        webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        await application.bot.set_webhook(url=webhook_url)
        print(f"Webhook ustawiony na: {webhook_url}")

    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=PORT)
