from flask import Flask, jsonify, request, render_template
import sqlite3
import time
import os
import threading
import telebot

# توکن ربات تلگرام
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
            last_resource_collect INTEGER,
            is_active INTEGER DEFAULT 0
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
    # 🌎 قاره آمریکا (آمریکا و ۷ کشور معروف دیگر)
    "USA": {"name": "آمریکا", "pack": "پک برتری هوایی ✈️"},
    "Canada": {"name": "کانادا", "pack": "پک منابع و معادن غنی 🍁"},
    "Brazil": {"name": "برزیل", "pack": "پک ارتش جنگل و کشاورزی ⚽"},
    "Argentina": {"name": "آرژانتین", "pack": "پک زرهی استراتژیک 🛡️"},
    "Mexico": {"name": "مکزیک", "pack": "پک مرزبانان سریع 🦅"},
    "Colombia": {"name": "کلمبیا", "pack": "پک عملیات ویژه کوهستان ⛰️"},
    "Chile": {"name": "شیلی", "pack": "پک کنترل سواحل اقیانوس 🌊"},
    "Peru": {"name": "پرو", "pack": "پک باستانی و پدافندی 🛕"},

    # 🇪🇺 اروپا (۱۰ کشور معروف شامل فرانسه، انگلیس، آلمان و دیگران)
    "UK": {"name": "انگلیس", "pack": "پک نیروی دریایی سلطنتی 🚢"},
    "France": {"name": "فرانسه", "pack": "پک زرهی زمینی و اتمی 🎖️"},
    "Germany": {"name": "آلمان", "pack": "پک صنعت و مهندسی پیشرفته ⚙️"},
    "Italy": {"name": "ایتالیا", "pack": "پک ناوگان مدیترانه ⚓"},
    "Spain": {"name": "اسپانیا", "pack": "پک استراتژی دریایی ⛵"},
    "Ukraine": {"name": "اوکراین", "pack": "پک مقاومت پهپادی 🛸"},
    "Poland": {"name": "لهستان", "pack": "پک سپر دفاع موشکی 🛡️"},
    "Sweden": {"name": "سوئد", "pack": "پک تسلیحات پیشرفته رادارگریز 📡"},
    "Netherlands": {"name": "هلند", "pack": "پک لجستیک و بنادر تجاری 🌐"},
    "Switzerland": {"name": "سوئیس", "pack": "پک بانکداری و امنیت مالی 🏦"},

    # 🌏 آسیا و خاورمیانه (۱۰ کشور معروف شامل ایران، اسرائیل، روسیه و دیگران)
    "Iran": {"name": "ایران", "pack": "پک موشکی نقطه‌زن 🚀"},
    "Israel": {"name": "اسرائیل", "pack": "پک جنگ سایبری و هکری 💻"},
    "Russia": {"name": "روسیه", "pack": "پک اتمی تزار ☢️"},
    "China": {"name": "چین", "pack": "پک ساخت و ساز سریع 🏭"},
    "Japan": {"name": "ژاپن", "pack": "پک فناوری رباتیک و هوش مصنوعی 🤖"},
    "India": {"name": "هند", "pack": "پک نیروی انسانی انبوه 🇮🇳"},
    "Turkey": {"name": "ترکیه", "pack": "پک پهپادهای رزمی بایرکار ✈️"},
    "SaudiArabia": {"name": "عربستان", "pack": "پک پتروشیمی و دلارهای نفتی 🛢️"},
    "SouthKorea": {"name": "کره جنوبی", "pack": "پک دفاع هوایی و الکترونیک ⚡"},
    "Pakistan": {"name": "پاکستان", "pack": "پک تسلیحات اتمی تاکتیکی ⚛️"}
}

admin_pending_country = {}

# ------ بخش ربات تلگرام ------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "فرمانده"
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()
    
    if not p:
        cursor.execute("""
            INSERT OR IGNORE INTO players (user_id, country_name, is_active, last_resource_collect)
            VALUES (?, ?, 0, ?)
        """, (user_id, name, int(time.time())))
        conn.commit()
    conn.close()
    
    bot.reply_to(message, f"سلام {name} عزیز! ⚔️\nبه ربات جنگ جهانی خوش آمدی.\n\n❌ حساب شما هنوز توسط ادمین تایید نشده و کشوری به شما اختصاص نیافته است. لطفاً منتظر بمانید.")

# ------ بخش مدیریت ادمین‌ها ------
@bot.message_handler(commands=['newadmin'])
def new_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ شما دسترسی به این دستور را ندارید.")
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
        bot.reply_to(message, f"✅ کاربر با آیدی `{target_id}` ادمین شد.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")
    finally:
        conn.close()

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# ------ دستور اختصاص کشور (/keshvar) ------
@bot.message_handler(commands=['keshvar'])
def keshvar_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ شما دسترسی به این دستور را ندارید.")
        return
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for key, val in SUPERPOWERS.items():
        markup.add(telebot.types.InlineKeyboardButton(f"{val['name']} ({val['pack']})", callback_data=f"set_country_{key}"))
    
    bot.reply_to(message, "🏛 **لطفاً کشور مورد نظر را انتخاب کنید:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_country_'))
def country_selected_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی غیرمجاز!", show_alert=True)
        return
        
    country_key = call.data.replace('set_country_', '')
    if country_key not in SUPERPOWERS:
        bot.answer_callback_query(call.id, "❌ کشور نامعتبر است.", show_alert=True)
        return
        
    admin_pending_country[call.from_user.id] = country_key
    bot.answer_callback_query(call.id, f"کشور {SUPERPOWERS[country_key]['name']} انتخاب شد.")
    bot.edit_message_text(
        f"✅ کشور **{SUPERPOWERS[country_key]['name']}** انتخاب شد.\n\nاکنون **آیدی عددی کاربر** را در قالب یک پیام ارسال کنید تا این کشور به او اختصاص یابد.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.from_user.id in admin_pending_country)
def get_user_id_for_country(message):
    admin_id = message.from_user.id
    if not is_admin(admin_id):
        return
        
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, "❌ آیدی عددی باید فقط شامل عدد باشد. دوباره ارسال کنید.")
        return
        
    country_key = admin_pending_country.pop(admin_id)
    c_info = SUPERPOWERS[country_key]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM players WHERE user_id = ?", (target_user_id,))
    player_exists = cursor.fetchone()
    
    start_cash = 1000000
    pack = c_info['pack']
    c_name = c_info['name']
    
    if player_exists:
        cursor.execute("""
            UPDATE players 
            SET country_name = ?, is_superpower = 1, special_pack = ?, cash = cash + ?, is_active = 1 
            WHERE user_id = ?
        """, (c_name, pack, start_cash, target_user_id))
    else:
        cursor.execute("""
            INSERTINTO players (user_id, country_name, is_superpower, special_pack, cash, is_active, last_resource_collect)
            VALUES (?, ?, 1, ?, ?, 1, ?)
        """, (target_user_id, c_name, pack, start_cash, int(time.time())))
        
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ با موفقیت کشور **{c_name}** به کاربر با آیدی `{target_user_id}` اختصاص یافت و حسابش فعال شد!", parse_mode="Markdown")
    
    try:
        bot.send_message(target_user_id, f"🎉 تبریک فرمانده!\nکشور شما **{c_name}** با موفقیت تایید و ثبت شد. هم اکنون می‌توانید وارد مینی‌اپ بازی شوید.")
    except:
        pass


# ------ بخش APIهای وب و فلاسک ------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/get_country/<int:user_id>', methods=['GET'])
def get_country(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()

    if not p or p[15] == 0:
        conn.close()
        return jsonify({"error": "Unauthorized", "message": "حساب شما هنوز توسط ادمین تایید نشده است."}), 403

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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()
    if not p or p[0] == 0:
        conn.close()
        return jsonify({"error": "دسترسی غیرمجاز یا تایید نشده"}), 403

    valid_types = ["gold_mines", "iron_mines", "oil_mines", "uranium_mines", "cash_factories"]
    if b_type not in valid_types:
        conn.close()
        return jsonify({"error": "نوع ساخت‌وساز نامعتبر است"}), 400

    cursor.execute("SELECT cash, gold_mines, iron_mines, oil_mines, uranium_mines, cash_factories FROM players WHERE user_id = ?", (user_id,))
    p_data = cursor.fetchone()

    cost = 100000
    col_map = {"gold_mines": 1, "iron_mines": 2, "oil_mines": 3, "uranium_mines": 4, "cash_factories": 5}
    current_count = p_data[col_map[b_type]]

    if current_count >= 3:
        conn.close()
        return jsonify({"error": "حداکثر ظرفیت (۳ عدد) برای این سازه تکمیل است!"}), 400

    if p_data[0] < cost:
        conn.close()
        return jsonify({"error": "بودجه کافی نیست!"}), 400

    cursor.execute(f"UPDATE players SET cash = cash - ?, {b_type} = {b_type} + 1 WHERE user_id = ?", (cost, user_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "سازه ساخته شد."})

@app.route('/api/market', methods=['POST'])
def market_action():
    data = request.json
    user_id = data.get('user_id')
    resource_type = data.get('resource')
    action = data.get('action')
    try:
        amount = int(data.get('amount', 1))
    except ValueError:
        amount = 1
        
    if amount <= 0:
        return jsonify({"error": "تعداد نامعتبر است"}), 400
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active, cash, iron, oil, gold, uranium FROM players WHERE user_id = ?", (user_id,))
    p = cursor.fetchone()
    
    if not p or p[0] == 0:
        conn.close()
        return jsonify({"error": "دسترسی غیرمجاز یا تایید نشده"}), 403
        
    cash = p[1]
    res_map = {"iron": p[2], "oil": p[3], "gold": p[4], "uranium": p[5]}
    current_res_val = res_map.get(resource_type, 0)
    
    market_prices = {
        "iron": {"buy": 10000, "sell": 1000},
        "oil": {"buy": 25000, "sell": 2500},
        "gold": {"buy": 100000, "sell": 40000},
        "uranium": {"buy": 60000, "sell": 6000}
    }
    
    if resource_type not in market_prices or action not in ["buy", "sell"]:
        conn.close()
        return jsonify({"error": "پارامترهای بازار نامعتبر است"}), 400
        
    prices = market_prices[resource_type]
    
    if action == "buy":
        total_cost = prices["buy"] * amount
        if cash < total_cost:
            conn.close()
            return jsonify({"error": f"بودجه کافی نداری! برای خرید {amount} عدد به {total_cost:,} دلار نیاز داری."}), 400
            
        cursor.execute(f"""
            UPDATE players 
            SET cash = cash - ?, {resource_type} = {resource_type} + ? 
            WHERE user_id = ?
        """, (total_cost, amount, user_id))
        
    elif action == "sell":
        if current_res_val < amount:
            conn.close()
            return jsonify({"error": f"موجودی کافی نداری! شما فقط {current_res_val} عدد از این منبع را دارید."}), 400
            
        total_revenue = prices["sell"] * amount
        cursor.execute(f"""
            UPDATE players 
            SET cash = cash + ?, {resource_type} = {resource_type} - ? 
            WHERE user_id = ?
        """, (total_revenue, amount, user_id))
        
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "تراکنش بازار با موفقیت انجام شد."})

init_db()

def start_bot():
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
