import os
import json
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp
import threading

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot działa poprawnie!"

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

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

async def check_and_send_shorts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Sprawdzam nowe Shortsy na wybranych kanałach...")
    
    last_seen = load_last_seen()
    
    # Bezpieczne opcje dla yt-dlp unikające błędów wyciągania playera
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'playlistend': 5,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    
    nowe_filmy_znalezione = False

    for kanal_url in KANALY_YT:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(kanal_url, download=False)
                if not info or 'entries' not in info:
                    continue
                
                entries = [e for e in info['entries'] if e]
                if not entries:
                    continue
                    
                ostatni_zapisany_id = last_seen.get(kanal_url)
                
                nowe_entries = []
                for entry in entries:
                    if entry.get('id') == ostatni_zapisany_id:
                        break
                    nowe_entries.append(entry)
                
                if entries:
                    last_seen[kanal_url] = entries[0].get('id')

                for entry in reversed(nowe_entries):
                    vid_id = entry.get('id')
                    vid_title = entry.get('title', 'Short')
                    if not vid_id:
                        continue
                        
                    video_url = f"https://www.youtube.com/watch?v={vid_id}"
                    await update.message.reply_text(f"⬇️ Pobieram nowy Short: {vid_title}")
                    
                    download_opts = {
                        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                        'outtmpl': 'temp_short.mp4',
                        'overwrites': True,
                        'quiet': True,
                        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
                    }
                    
                    with yt_dlp.YoutubeDL(download_opts) as ydl_down:
                        ydl_down.download([video_url])
                    
                    if os.path.exists('temp_short.mp4'):
                        with open('temp_short.mp4', 'rb') as video_file:
                            await context.bot.send_video(
                                chat_id=update.effective_chat.id,
                                video=video_file,
                                caption=f"🎬 **{vid_title}**\n🔗 {video_url}"
                            )
                        os.remove('temp_short.mp4')
                        nowe_filmy_znalezione = True

            except Exception as e:
                await update.message.reply_text(f"⚠️ Błąd przy kanale: {str(e)}")

    save_last_seen(last_seen)
    
    if not nowe_filmy_znalezione:
        await update.message.reply_text("✨ Brak nowych Shortsów od ostatniego sprawdzania!")
    else:
        await update.message.reply_text("✅ Wszystkie nowe Shortsy zostały wysłane!")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", check_and_send_shorts))
    application.add_handler(CommandHandler("sprawdz", check_and_send_shorts))
    
    print("Bot ruszył i nasłuchuje w tle!")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

if __name__ == '__main__':
    t = threading.Thread(target=run_bot)
    t.start()
    app_flask.run(host='0.0.0.0', port=PORT)
