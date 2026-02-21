import telebot
import os
import time
import threading
from flask import Flask

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

db = {}
upload_sessions = {}

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()

    if len(args) > 1:
        media_id = args[1]
        files = db.get(media_id)

        if not files:
            bot.send_message(message.chat.id,"❌ No media found.")
            return

        sent = []

        for f in files:
            t = f["type"]
            fid = f["file_id"]

            if t=="photo":
                m=bot.send_photo(message.chat.id,fid,caption=f.get("caption",""))
            elif t=="video":
                m=bot.send_video(message.chat.id,fid,caption=f.get("caption",""))
            elif t=="document":
                m=bot.send_document(message.chat.id,fid)
            elif t=="audio":
                m=bot.send_audio(message.chat.id,fid)
            elif t=="voice":
                m=bot.send_voice(message.chat.id,fid)
            elif t=="animation":
                m=bot.send_animation(message.chat.id,fid)
            elif t=="sticker":
                m=bot.send_sticker(message.chat.id,fid)

            sent.append(m.message_id)

        note=bot.send_message(message.chat.id,"⚠️ Auto delete in 10 minutes")
        sent.append(note.message_id)

        def delete_later(chat,ids):
            time.sleep(600)
            for i in ids:
                try: bot.delete_message(chat,i)
                except: pass

        threading.Thread(target=delete_later,args=(message.chat.id,sent)).start()

    else:
        bot.send_message(message.chat.id,"📤 Type /upload to send files")

# ---------- UPLOAD ----------
@bot.message_handler(commands=['upload'])
def upload(message):
    from telebot.types import ReplyKeyboardMarkup
    k=ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("✅")

    media_id=str(int(time.time()))
    upload_sessions[message.chat.id]={"id":media_id,"files":[]}

    bot.send_message(message.chat.id,"Send media, press ✅ when done",reply_markup=k)

# ---------- HANDLE MEDIA ----------
@bot.message_handler(content_types=['photo','video','audio','voice','document','animation','sticker','text'])
def handle(message):
    session=upload_sessions.get(message.chat.id)
    if not session: return

    if message.text=="✅":
        files=session["files"]
        if not files:
            bot.send_message(message.chat.id,"❌ No media uploaded")
            return

        mid=session["id"]
        db[mid]=files
        link=f"https://t.me/{bot.get_me().username}?start={mid}"

        bot.send_message(message.chat.id,f"✅ Done\n{link}")
        upload_sessions.pop(message.chat.id)
        return

    entry=None
    if message.photo: entry={"type":"photo","file_id":message.photo[-1].file_id,"caption":message.caption}
    elif message.video: entry={"type":"video","file_id":message.video.file_id,"caption":message.caption}
    elif message.document: entry={"type":"document","file_id":message.document.file_id}
    elif message.audio: entry={"type":"audio","file_id":message.audio.file_id}
    elif message.voice: entry={"type":"voice","file_id":message.voice.file_id}
    elif message.animation: entry={"type":"animation","file_id":message.animation.file_id}
    elif message.sticker: entry={"type":"sticker","file_id":message.sticker.file_id}

    if entry:
        session["files"].append(entry)
        bot.send_message(message.chat.id,"Saved. Send more or press ✅")

# ---------- RUN BOT + SERVER ----------
def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot).start()

@app.route('/')
def home():
    return "Bot alive"

if __name__ == "__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
