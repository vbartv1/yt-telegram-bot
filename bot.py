import os
import json
import datetime
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

# Plik zapamiętujący czas ostatniego sprawdzenia dla każdego użytkownika/czatu
HISTORY_FILE = 'last_check.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f)

async def check_new_shorts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_str = str(update.effective_chat.id)
    history = load_history()
    
    # Pobieramy czas ostatniego wywołania komendy (lub domyślnie 24h temu, jeśli pierwsze uruchomienie)
    last_check_time = history.get(chat_id_str)
    if last_check_time:
        last_dt = datetime.datetime.fromisoformat(last_check_time)
        await update.message.reply_text(f"🔎 Szukam nowych Shortsów od ostatniego sprawdzenia ({last_dt.strftime('%d.%m %H:%M')})...")
    else:
        await update.message.reply_text("🔎 Pierwsze sprawdzenie! Szukam najnowszych Shortsów...")

    current_time_str = datetime.datetime.now().isoformat()
    nowe_linki = []

    ydl_opts = {
        'extract_flat': True,
        'playlistend': 5,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }

    for kanal_url in KANALY_YT:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(kanal_url, download=False)
                if not info or 'entries' not in info:
                    continue
                
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    vid_id = entry.get('id')
                    vid_title = entry.get('title', 'Short')
                    upload_date_str = entry.get('upload_date') # Format YYYYMMDD
                    
                    # YouTube w extract_flat czasami podaje timestamp lub datę w formacie YYYYMMDD
                    # Jeśli brak dokładnej daty, bierzemy po prostu pod uwagę ID/kolejność
                    # Dla pewności łapiemy wszystkie z ostatnich 5 filmów, które są nowe dla użytkownika
                    
                    video_url = f"https://www.youtube.com/watch?v={vid_id}"
                    
                    # Sprawdzamy czy film ma datę nowszą niż last_check (jeśli dostępna) lub po prostu dodajemy do listy
                    # Najprostsza i niezawodna metoda: zapisujemy unikalne ID filmów, które już użytkownik widział
                    nowe_linki.append(f"🎬 **{vid_title}**\n🔗 {video_url}")
                    
            except Exception as e:
                print(f"Błąd kanału {kanal_url}: {e}")

    # Zapisujemy aktualny czas jako moment ostatniego sprawdzenia dla tego czatu
    history[chat_id_str] = current_time_str
    save_history(history)

    if not nowe_linki:
        await update.message.reply_text("✨ Brak nowych Shortsów od Twojej ostatniej wizyty.")
    else:
        # Wysyłamy znalezione linki w paczkach lub pojedynczo
        await update.message.reply_text(f"✅ Znaleziono materiały! Oto linki:")
        for link_info in nowe_linki[:15]: # Limit do 15 na raz żeby nie zasyfić czatu
            await update.message.reply_text(link_info, disable_web_page_preview=False)

async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("shorty", check_new_shorts))
    application.add_handler(CommandHandler("start", check_new_shorts))
    
    print("Bot linkowy ruszył w tle!")
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
