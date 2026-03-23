import telebot
import subprocess
import os
import sqlite3
import psutil
from telebot import types
from flask import Flask
from threading import Thread

# --- CONFIG ---
API_TOKEN = '8645736508:AAEdKR923fPgSYrSX1JuAGW1w5T5ClPWi-I'
ADMIN_ID = 7841488503 
bot = telebot.TeleBot(API_TOKEN)

CHANNELS = [
    {'id': -1002911188809, 'link': 'https://t.me/+094OeUOEuDthM2Q1'},
    {'id': -1003536181792, 'link': 'https://t.me/Eternity_tools'}
]

BASE_DIR = "user_bots"
DB_NAME = "eternity_final_v6.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("CREATE TABLE IF NOT EXISTS bots (uid INTEGER, fname TEXT, pid INTEGER, PRIMARY KEY(uid, fname))")
    conn.commit(); conn.close()

init_db()

# --- WEB SERVER ---
server = Flask('')
@server.route('/')
def home(): return "Eternity Pro V6 Online"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- STATUS CHECK LOGIC ---
def get_bot_status(uid, fname):
    conn = sqlite3.connect(DB_NAME)
    res = conn.execute("SELECT pid FROM bots WHERE uid=? AND fname=?", (uid, fname)).fetchone()
    conn.close()
    if res:
        pid = res[0]
        try:
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    return "Running 🟢", True
        except: pass
    return "Stopped 🔴", False

def check_sub(uid):
    for ch in CHANNELS:
        try:
            s = bot.get_chat_member(ch['id'], uid).status
            if s in ['left', 'kicked']: return False
        except: return False
    return True

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.chat.id
    if not check_sub(uid):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            markup.add(types.InlineKeyboardButton(f"Join Channel {i} 🔗", url=ch['link']))
        markup.add(types.InlineKeyboardButton("🔄 VERIFY JOIN", callback_data="verify"))
        bot.send_message(uid, "❌ <b>Access Denied!</b>\n\nJoin our channels to use <b>Eternity Pro Hosting</b>. High-speed, 24/7 uptime for all your bots!", reply_markup=markup, parse_mode="HTML")
        return
    
    # Eternity Ads Bot Jaisa UI (Support/Official Start Menu Pe)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🖥 OPEN DASHBOARD", callback_data="open_dash"),
        types.InlineKeyboardButton("📢 OFFICIAL CHANNEL", url="https://t.me/Eternity_tools"),
        types.InlineKeyboardButton("🛠 SUPPORT", url="https://t.me/itachi_era")
    )
    
    welcome_text = (
        "✨ <b>Eternity Pro Hosting</b>\n"
        "________________________________________\n\n"
        "Welcome to the most powerful hosting bot.\n"
        "Deploy your code and keep it running 24/7.\n\n"
        "<b>Developed by:</b> @itachi_era"
    )
    bot.send_message(uid, welcome_text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.message.chat.id
    data = call.data

    if data == "verify":
        if check_sub(uid):
            bot.delete_message(uid, call.message.message_id)
            welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

    elif data == "open_dash":
        # Dashboard ke andar se support/official hata diya
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚀 DEPLOY CODE", callback_data="deploy_py"),
            types.InlineKeyboardButton("🤖 YOUR BOTS", callback_data="my_bots")
        )
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="back_to_start"))
        
        bot.edit_message_text("🖥 <b>MAIN DASHBOARD</b>\nChoose an action to manage your server.", uid, call.message.message_id, reply_markup=markup, parse_mode="HTML")

    elif data == "back_to_start":
        bot.delete_message(uid, call.message.message_id)
        welcome(call.message)

    elif data == "deploy_py":
        msg = bot.send_message(uid, "📤 <b>Upload Bot File:</b>\nSend your main <code>.py</code> file now.", parse_mode="HTML")
        bot.register_next_step_handler(msg, save_py)

    elif data == "my_bots":
        user_path = os.path.join(BASE_DIR, str(uid))
        if not os.path.exists(user_path) or not os.listdir(user_path):
            bot.answer_callback_query(call.id, "📂 No bots found!", show_alert=True)
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for f in os.listdir(user_path):
            if f.endswith(".py"):
                status_text, _ = get_bot_status(uid, f)
                markup.add(types.InlineKeyboardButton(f"{status_text} | {f}", callback_data=f"manage_{f}"))
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="open_dash"))
        bot.edit_message_text("🤖 <b>YOUR BOTS LIST</b>", uid, call.message.message_id, reply_markup=markup, parse_mode="HTML")

    elif data.startswith("manage_"):
        fname = data.split("_")[1]
        status_text, is_running = get_bot_status(uid, fname)
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("▶️ START", callback_data=f"start_{fname}"),
            types.InlineKeyboardButton("🛑 STOP", callback_data=f"stop_{fname}")
        )
        markup.add(types.InlineKeyboardButton("🗑 DELETE", callback_data=f"del_{fname}"),
                   types.InlineKeyboardButton("🔙 BACK", callback_data="my_bots"))
        
        bot.edit_message_text(f"⚙️ <b>Managing:</b> <code>{fname}</code>\n<b>Status:</b> {status_text}", 
                             uid, call.message.message_id, reply_markup=markup, parse_mode="HTML")

    elif data.startswith(("start_", "stop_", "del_")):
        action, fname = data.split("_")
        user_path = os.path.join(BASE_DIR, str(uid), fname)
        conn = sqlite3.connect(DB_NAME)

        if action == "start":
            _, running = get_bot_status(uid, fname)
            if running:
                bot.answer_callback_query(call.id, "⚠️ Already Running!", show_alert=True)
            else:
                log_f = open(f"{user_path}.log", "w")
                p = subprocess.Popen(["python", user_path], stdout=log_f, stderr=log_f)
                conn.execute("INSERT OR REPLACE INTO bots VALUES (?, ?, ?)", (uid, fname, p.pid))
                bot.answer_callback_query(call.id, "🚀 Bot Started Successfully!", show_alert=True)

        elif action == "stop":
            res = conn.execute("SELECT pid FROM bots WHERE uid=? AND fname=?", (uid, fname)).fetchone()
            if res:
                try:
                    p = psutil.Process(res[0])
                    p.terminate()
                    p.wait(timeout=2)
                except: pass
                conn.execute("DELETE FROM bots WHERE uid=? AND fname=?", (uid, fname))
                bot.answer_callback_query(call.id, "🛑 Bot Stopped!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ Bot is not running.", show_alert=True)

        elif action == "del":
            res = conn.execute("SELECT pid FROM bots WHERE uid=? AND fname=?", (uid, fname)).fetchone()
            if res:
                try: psutil.Process(res[0]).terminate()
                except: pass
            if os.path.exists(user_path): os.remove(user_path)
            conn.execute("DELETE FROM bots WHERE uid=? AND fname=?", (uid, fname))
            bot.answer_callback_query(call.id, "🗑 Deleted!", show_alert=True)

        conn.commit(); conn.close()
        # Immediate UI Refresh
        handle_query(types.CallbackQuery(call.id, call.from_user, call.message, call.chat_instance, "my_bots" if action=="del" else f"manage_{fname}"))

# --- FILE LOGIC ---
def save_py(message):
    if not message.document or not message.document.file_name.endswith(".py"):
        bot.send_message(message.chat.id, "❌ Error: Send only <code>.py</code> files.", parse_mode="HTML")
        return
    uid = message.chat.id
    u_dir = os.path.join(BASE_DIR, str(uid))
    if not os.path.exists(u_dir): os.makedirs(u_dir)
    f_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(f_info.file_path)
    file_path = os.path.join(u_dir, message.document.file_name)
    with open(file_path, 'wb') as f: f.write(downloaded)
    
    msg = bot.send_message(uid, "✅ Script Saved. Now send <b>requirements.txt</b>:")
    bot.register_next_step_handler(msg, save_req, message.document.file_name)

def save_req(message, py_name):
    uid = message.chat.id
    u_dir = os.path.join(BASE_DIR, str(uid))
    req_path = os.path.join(u_dir, "requirements.txt")
    f_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(f_info.file_path)
    with open(req_path, 'wb') as f: f.write(downloaded)
    
    bot.send_message(uid, "📦 <b>Installing & Starting...</b>", parse_mode="HTML")
    subprocess.run(["pip", "install", "-r", req_path])
    
    py_path = os.path.join(u_dir, py_name)
    log_f = open(f"{py_path}.log", "w")
    p = subprocess.Popen(["python", py_path], stdout=log_f, stderr=log_f)
    
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO bots VALUES (?, ?, ?)", (uid, py_name, p.pid))
    conn.commit(); conn.close()
    
    bot.send_message(uid, f"🚀 <b>Deployment Success!</b>\nYour bot <code>{py_name}</code> is now running 24/7.", reply_markup=main_dash_markup(), parse_mode="HTML")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling()