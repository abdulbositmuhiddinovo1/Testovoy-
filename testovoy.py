import os
import requests
import telebot
from flask import Flask
from threading import Thread

# --- 1. SOZLAMALAR ---
TOKEN = "8609774012:AAESLeJZrVi6iuPGyitKWNSpolCOtk_tUSU"
ADMIN_ID = 8078471553

# Supabase sozlamalari
SUPABASE_URL = "https://pynycwafilbsuaolsssp.supabase.co/rest/v1"
SUPABASE_KEY = "MLBB2210.2010"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

bot = telebot.TeleBot(TOKEN)

# --- 2. FLASK WEB SERVER (Render port xatosi bermasligi uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot ishlayapti va Supabase'ga ulangan!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_flask).start()

# --- 3. TELEGRAM BOT HANDLERLARI ---

# /start buyrug'i
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    # Foydalanuvchini Supabase'ga saqlash
    try:
        requests.post(
            f"{SUPABASE_URL}/users",
            headers={**HEADERS, "Prefer": "resolution=ignore-duplicates"},
            json={"user_id": user_id}
        )
    except Exception as e:
        print(f"Xatolik (user save): {e}")

    welcome_text = (
        "✨ *Assalomu alaykum, hurmatli foydalanuvchi!*\n\n"
        "🎬 *Kinolar olamiga xush kelibsiz!*\n\n"
        "🍿 Menga kino kodini yuboring, men darhol sizga o'sha kinoni topib beraman."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# Admin uchun /stat buyrug'i
@bot.message_handler(commands=['stat'])
def get_stats(message):
    if message.from_user.id == ADMIN_ID:
        try:
            # Supabase'dan foydalanuvchilar sonini olish
            resp = requests.get(
                f"{SUPABASE_URL}/users?select=user_id",
                headers={**HEADERS, "Range": "0-0", "Prefer": "count=exact"}
            )
            content_range = resp.headers.get("content-range", "")
            user_count = 0
            if "/" in content_range:
                user_count = int(content_range.split("/")[1])
            else:
                user_count = len(resp.json()) if resp.ok else 0
        except Exception as e:
            user_count = "Noma'lum"

        bot.reply_to(
            message, 
            f"📊 **Bot statistikasi (Supabase):**\n\n👥 Barcha foydalanuvchilar: **{user_count} ta**", 
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "⚠️ Bu buyruq faqat admin uchun!")

# Admin uchun /add buyrug'i
@bot.message_handler(commands=['add'])
def start_add_movie(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(
            message.chat.id, 
            "🎬 **Yangi kino kodini kiriting:**\n(Masalan: 101)", 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_movie_code)

def process_movie_code(message):
    code = message.text.strip()
    msg = bot.send_message(message.chat.id, f"📥 Endi `{code}` kodi uchun video faylni yuboring:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_movie_video, code)

def process_movie_video(message, code):
    if message.content_type == 'video':
        file_id = message.video.file_id
        try:
            requests.post(
                f"{SUPABASE_URL}/movies",
                headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                json={"code": code, "file_id": file_id}
            )
            bot.reply_to(message, f"✅ **Kino Supabase'ga saqlandi!**\n🎬 Kodi: `{code}`", parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ Saqlashda xatolik yuz berdi: {e}")
    else:
        bot.reply_to(message, "❌ Iltimos, faqat **video** yuboring!")

# Oddiy video kelganda (caption'da kodi bo'lsa) saqlash
@bot.message_handler(content_types=['video'])
def add_movie_by_caption(message):
    if message.from_user.id == ADMIN_ID and message.caption:
        code = message.caption.strip()
        file_id = message.video.file_id

        try:
            requests.post(
                f"{SUPABASE_URL}/movies",
                headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                json={"code": code, "file_id": file_id}
            )
            bot.reply_to(message, f"✅ **Kino Supabase'ga saqlandi!**\n🎬 Kodi: `{code}`", parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ Xatolik: {e}")

# Kinoni kodi bo'yicha qidirish
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    code = message.text.strip()
    chat_id = message.chat.id
    
    # Har bir yozgan odamni bazaga qo'shib borish
    try:
        requests.post(
            f"{SUPABASE_URL}/users",
            headers={**HEADERS, "Prefer": "resolution=ignore-duplicates"},
            json={"user_id": chat_id}
        )
    except:
        pass

    # Kinoni Supabase'dan qidirish
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/movies?code=eq.{code}&select=file_id",
            headers=HEADERS
        )
        data = resp.json()
        if data and len(data) > 0:
            file_id = data[0]["file_id"]
            bot.send_video(
                chat_id, 
                file_id, 
                caption=f"🎬 *Kino kodi:* `{code}`\n✨ Yoqimli tomosha!", 
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(message, "❌ *Kechirasiz, bu kod bo'yicha kino topilmadi.*", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Qidirishda xatolik: {e}")

# --- 4. BOTNI ISHGA TUSHIRISH ---
if __name__ == '__main__':
    print("Bot ishga tushdi va Supabase'ga ulandi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
