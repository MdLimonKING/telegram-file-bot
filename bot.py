import telebot
import os
import time
import threading
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# memory database (simple)
db = {}
upload_sessions = {}

# -------- START COMMAND --------
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()

    # if opened from link
    if len(args) > 1:
        media_id = args[1]
        files = db.get(media_id)

        if not files:
            bot.send_message(message.chat.id, "❌ No media found for this link.")
            return

        sent_msgs = []

        for f in files:
            m = None
            t = f["type"]
            fid = f["file_id"]

            if t == "photo":
                m = bot.send_photo(message.chat.id, fid, caption=f.get("caption",""))
            elif t == "video":
                m = bot.send_video(message.chat.id, fid, caption=f.get("caption",""))
            elif t == "audio":
                m = bot.send_audio(message.chat.id, fid)
            elif t == "voice":
                m = bot.send_voice(message.chat.id, fid)
            elif t == "document":
                m = bot.send_document(message.chat.id, fid)
            elif t == "animation":
                m = bot.send_animation(message.chat.id, fid)
            elif t == "sticker":
                m = bot.send_sticker(message.chat.id, fid)

            if m:
                sent_msgs.append(m.message_id)

        note = bot.send_message(
            message.chat.id,
            "⚠️ Files will be auto deleted after 10 minutes."
        )
        sent_msgs.append(note.message_id)

        # delete after 10 minutes
        def delete_later(chat_id, ids):
            time.sleep(600)
            for mid in ids:
                try:
                    bot.delete_message(chat_id, mid)
                except:
                    pass

        threading.Thread(target=delete_later, args=(message.chat.id, sent_msgs)).start()

    else:
        bot.send_message(
            message.chat.id,
            "📤 Welcome!\n\nType /upload to start uploading files."
        )

# -------- UPLOAD COMMAND --------
@bot.message_handler(commands=['upload'])
def upload(message):
    media_id = str(int(time.time()))
    upload_sessions[message.chat.id] = {"id": media_id, "files": []}
    bot.send_message(message.chat.id, "👉 Send your media files now. Send DONE when finished.")

# -------- HANDLE MEDIA --------
@bot.message_handler(content_types=[
    'photo','video','audio','voice','document','animation','sticker','text'
])
def handle_media(message):

    session = upload_sessions.get(message.chat.id)

    if not session:
        return

    if message.text == "DONE":
        files = session["files"]
        media_id = session["id"]

        if not files:
            bot.send_message(message.chat.id, "❌ No media uploaded.")
            return

        db[media_id] = files
        link = f"https://t.me/{bot.get_me().username}?start={media_id}"

        bot.send_message(message.chat.id, f"✅ Upload complete!\nShare this link:\n{link}")
        upload_sessions.pop(message.chat.id)
        return

    entry = None

    if message.photo:
        entry = {"type":"photo","file_id":message.photo[-1].file_id,"caption":message.caption}
    elif message.video:
        entry = {"type":"video","file_id":message.video.file_id,"caption":message.caption}
    elif message.audio:
        entry = {"type":"audio","file_id":message.audio.file_id}
    elif message.voice:
        entry = {"type":"voice","file_id":message.voice.file_id}
    elif message.document:
        entry = {"type":"document","file_id":message.document.file_id}
    elif message.animation:
        entry = {"type":"animation","file_id":message.animation.file_id}
    elif message.sticker:
        entry = {"type":"sticker","file_id":message.sticker.file_id}

    if entry:
        session["files"].append(entry)
        bot.send_message(message.chat.id, "✅ Saved. Send more or DONE to finish.")
    else:
        bot.send_message(message.chat.id, "❌ Send media only.")

# -------- WEBHOOK --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def home():
    return "Bot running"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.polling(none_stop=True)
