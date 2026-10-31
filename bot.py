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
    return "Bot linków działa poprawnie!"

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

KANALY_YT = [
    'https://www.youtube.com/@giga.shoty67/shorts',
    'https://www.youtube.com/@tfardyyy/shorts',
    'https://www.youtube.com/@Menel_CS/shorts',
    'https://www.youtube.com/@alphajestem/shorts',
    'https://www.youtube.com/@CEESOWESHOTY/shorts'
]

# Plik zapamiętujący ostatnio widziane ID filmów dla każdego kanału
LAST_SEEN_FILE = 'seen_shorts.json'

def load_seen():
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_seen(data):
    with open(LAST_SEEN_FILE, 'w') as f:
        json.dump(data, f)

async def check_new_shorts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Sprawdzam, czy pojawiło się coś nowego...")
    
    seen_data = load_seen()
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 5,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }
    
    nowe_linki_znalezione = False

    for kanal_url in KANALY_YT:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(kanal_url, download=False)
                if not info or 'entries' not in info:
                    continue
                
                entries = [e for e in info['entries'] if e]
                if not entries:
                    continue
                
                # Pobieramy zapisane ID ostatniego filmu dla tego kanału
                ostatnio_widziany_id = seen_data.get(kanal_url)
                
                nowe_filmy_z_kanalu = []
                for entry in entries:
                    vid_id = entry.get('id')
                    if vid_id == ostatnio_widziany_id:
                        break # Dotarliśmy do momentu, który już znamy
                    nowe_filmy_z_kanalu.append(entry)
                
                # Jeśli to pierwsze uruchomienie dla kanału, zapamiętaj najnowszy, ale nic nie wysyłaj lub wyślij najnowszy
                if ostatnio_widziany_id is None and entries:
                    seen_data[kanal_url] = entries[0].get('id')
                    continue

                if nowe_filmy_z_kanalu:
                    # Aktualizujemy najnowszy ID na samej górze listy
                    seen_data[kanal_url] = entries[0].get('id')
                    
                    # Wysyłamy te, których użytkownik jeszcze nie widział (od najstarszego do najnowszego)
                    for entry in reversed(nowe_filmy_z_kanalu):
                        vid_id = entry.get('id')
                        vid_title = entry.get('title', 'Short')
                        video_url = f"https://www.youtube.com/watch?v={vid_id}"
                        
                        await update.message.reply_text(f"🎬 **{vid_title}**\n🔗 {video_url}")
                        nowe_linki_znalezione = True

            except Exception as e:
                print(f"Błąd kanału {kanal_url}: {e}")

    save_seen(seen_data)

    if not nowe_linki_znalezione:
        await update.message.reply_text("✨ Brak nowych Shortsów od Twojego ostatniego sprawdzenia!")
    else:
        await update.message.reply_text("✅ To wszystko! Obejrzałeś najnowsze nowości.")

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("shorty", check_new_shorts))
    application.add_handler(CommandHandler("start", check_new_shorts))
    
    print("Bot ruszył i nasłuchuje!")
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
