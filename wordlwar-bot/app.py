from flask import Flask, jsonify, request, render_template
import sqlite3
import time
import os
import threading
import telebot

# ۱. توکن ربات تلگرام
TOKEN = '8981061980:AAEKqC2myhSzjsURvMEpRjoZzxmF_IeTghQ'
bot = telebot.TeleBot(TOKEN)

# آیدی عددی مالک ربات
OWNER_ID = 6368372772

app = Flask(__name__)
DB_NAME = "world_war_game.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # جدول بازیکنان
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            country_name TEXT,
            is_superpower INTEGER DEFAULT 0,
            special_pack TEXT,
            gold INTEGER DEFAULT 100000,
            cash INTEGER DEFAULT 500000,
            iron INTEGER DEFAULT 1000,
            oil INTEGER DEFAULT 1000,
            uranium INTEGER DEFAULT 0,
            gold_mines INTEGER DEFAULT 0,
            iron_mines INTEGER DEFAULT 0,
            oil_mines INTEGER DEFAULT 0,
            uranium_mines INTEGER DEFAULT 0,
            cash_factories INTEGER DEFAULT 0,
            last_resource_collect INTEGER
        )
    """)
    # جدول ادمین‌ها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

SUPERPOWERS = {
    "Russia": {"name": "روسیه", "pack": "پک اتمی تزار ☢️"},
    "USA": {"name": "آمریکا", "pack": "پک برتری هوایی ✈️"},
    "Iran": {"name": "ایران", "pack": "پک موشکی نقطه‌زن 🚀"},
    "UK": {"name": "انگلیس", "pack": "پک نیروی دریایی سلطنتی 🚢"},
    "France": {"name": "فرانسه", "pack": "پک زرهی زمینی 🎖️"},
    "Israel": {"name": "اسرائیل", "pack": "پک جنگ سایبری و هکری 💻"},
    "China": {"name": "چین", "pack": "پک ساخت و ساز سریع 🏭"}
}

# ------ بخش ربات تلگرام ------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "فرمانده"
    bot.reply_to(message, f"سلام {name} عزیز! ⚔️\nبه ربات جنگ جهانی خوش آمدی.\nمینی‌اپ بازی فعال و آماده استفاده است.")

# ------ بخش مدیریت ادمین‌ها ------
@bot.message_handler(commands=['newadmin'])
def new_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما دسترسی به این دستور را ندارید (مخصوص مالک ربات است).")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ روش استفاده صحیح:\n`/newadmin <user_id>`", parse_mode="Markdown")
        return
    
    try:
        target_id = int(args[1])
    except ValueError:
        bot.reply_to(message, "❌ آیدی عددی نامعتبر است.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (target_id,))
        conn.commit()
        bot.reply_to(message, f"✅ کاربر با آیدی `{target_id}` با موفقیت به عنوان ادمین ثبت شد.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در ثبت ادمین: {e}")
    finally:
        conn.close()

@bot.message_handler(commands=['adminlist'])
def admin_list(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما دسترسی به این دستور را ندارید.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    admins = cursor.fetchall()
    conn.close()
    
    if not admins:
        bot.reply_to(message, "📋 هیچ ادمینی تاکنون ثبت نشده است.")
        return
    
    markup = telebot.types.InlineKeyboardMarkup()
    text = "📋 **لیست ادمین‌های ربات:**\n\n"
    for row in admins:
        uid = row[0]
        text += f"👤 آیدی: `{uid}`\n"
        markup.add(telebot.types.InlineKeyboardButton(f"🗑️ حذف ادمین {uid}", callback_data=f"del_admin_{uid}"))
    
    bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_admin_'))
def remove_admin_callback(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ شما مالک ربات نیستید!", show_alert=True)
        return
    
    target_id = int(call.data.replace('del_admin_', ''))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, f"ادمین {target_id} با موفقیت حذف شد.")
    try:
        bot.edit_message_text("✅ این ادمین از لیست مدیریت حذف شد.", call.message.chat.id, call.message.message_id)
    except:
        pass


# ------ بخش APIهای وب و فلاسک ------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id')
    country_name = data.get('country_name', 'کشور ناشناس')
    selected_superpower = data.get('superpower_key', 'Iran')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()

    if not player:
        is_sp = 1 if selected_superpower in SUPERPOWERS else 0
        pack = SUPERPOWERS[selected_superpower]['pack'] if is_sp else "پک معمولی"
        start_cash = 1000000 if is_sp else 500000
        
        cursor.execute("""
            INSERT INTO players (user_id, country_name, is_superpower, special_pack, cash, last_resource_collect)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, country_name, is_sp, pack, start_cash, int(time.time())))
        conn.commit()

    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/get_country/<int:user_id>', methods=['GET'])
def get_country(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()

    if not p:
        conn.close()
        return jsonify({"error": "Player not found"}), 404

    now = int(time.time())
    last_collect = p[14] if p[14] else now
    intervals = (now - last_collect) // 7200

    if intervals > 0:
        new_gold = p[4] + (intervals * p[9] * 500)
        new_iron = p[6] + (intervals * p[10] * 800)
        new_oil = p[7] + (intervals * p[11] * 1000)
        new_uranium = p[8] + (intervals * p[12] * 100)
        new_cash = p[5] + (intervals * p[13] * 200000)

        cursor.execute("""
            UPDATE players SET cash=?, gold=?, iron=?, oil=?, uranium=?, last_resource_collect=?
            WHERE user_id=?
        """, (new_cash, new_gold, new_iron, new_oil, new_uranium, last_collect + (intervals * 7200), user_id))
        conn.commit()
        cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        p = cursor.fetchone()

    conn.close()

    return jsonify({
        "user_id": p[0],
        "country_name": p[1],
        "is_superpower": p[2],
        "special_pack": p[3],
        "cash": p[5],
        "gold": p[4],
        "iron": p[6],
        "oil": p[7],
        "uranium": p[8],
        "buildings": {
            "gold_mines": p[9],
            "iron_mines": p[10],
            "oil_mines": p[11],
            "uranium_mines": p[12],
            "cash_factories": p[13]
        }
    })

@app.route('/api/build', methods=['POST'])
def build():
    data = request.json
    user_id = data.get('user_id')
    b_type = data.get('type')

    valid_types = ["gold_mines", "iron_mines", "oil_mines", "uranium_mines", "cash_factories"]
    if b_type not in valid_types:
        return jsonify({"error": "نوع ساخت‌وساز نامعتبر است"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT cash, gold_mines, iron_mines, oil_mines, uranium_mines, cash_factories FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()

    if not p:
        conn.close()
        return jsonify({"error": "کاربر یافت نشد"}), 404

    cost = 100000
    col_map = {"gold_mines": 1, "iron_mines": 2, "oil_mines": 3, "uranium_mines": 4, "cash_factories": 5}
    current_count = p[col_map[b_type]]

    if current_count >= 3:
        conn.close()
        return jsonify({"error": "حداکثر ظرفیت (۳ عدد) برای این سازه تکمیل است!"}), 400

    if p[0] < cost:
        conn.close()
        return jsonify({"error": "بودجه کافی نیست!"}), 400

    cursor.execute(f"UPDATE players SET cash = cash - ?, {b_type} = {b_type} + 1 WHERE user_id = ?", (cost, user_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "سازه ساخته شد."})

# ------ مسیر API بازار خرید و فروش منابع ------
@app.route('/api/market', methods=['POST'])
def market_action():
    data = request.json
    user_id = data.get('user_id')
    resource_type = data.get('resource') # iron, oil, gold, uranium
    action = data.get('action') # buy, sell
    
    market_prices = {
        "iron": {"buy": 10000, "sell": 1000},
        "oil": {"buy": 25000, "sell": 2500},
        "gold": {"buy": 100000, "sell": 40000}, # طلا (استثنا)
        "uranium": {"buy": 60000, "sell": 6000}    # اورانیوم اصلاح شده
    }
    
    if resource_type not in market_prices or action not in ["buy", "sell"]:
        return jsonify({"error": "پارامترهای بازار نامعتبر است"}), 400
        
    prices = market_prices[resource_type]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT cash, iron, oil, gold, uranium FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()
    
    if not p:
        conn.close()
        return jsonify({"error": "کاربر یافت نشد"}), 404
        
    cash = p[0]
    res_map = {"iron": p[1], "oil": p[2], "gold": p[3], "uranium": p[4]}
    current_res_val = res_map[resource_type]
    
    if action == "buy":
        cost = prices["buy"]
        if cash < cost:
            conn.close()
            return jsonify({"error": "بودجه کافی برای خرید این منبع را نداری!"}), 400
            
        cursor.execute(f"""
            UPDATE players 
            SET cash = cash - ?, {resource_type} = {resource_type} + 1 
            WHERE user_id = ?
        """, (cost, user_id))
        
    elif action == "sell":
        if current_res_val < 1:
            conn.close()
            return jsonify({"error": "موجودی این منبع برای فروش کافی نیست!"}), 400
            
        revenue = prices["sell"]
        cursor.execute(f"""
            UPDATE players 
            SET cash = cash + ?, {resource_type} = {resource_type} - 1 
            WHERE user_id = ?
        """, (revenue, user_id))
        
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "تراکنش بازار با موفقیت انجام شد."})

# ------ اجرای دیتابیس و روشن کردن Thread ربات ------
init_db()

def start_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
