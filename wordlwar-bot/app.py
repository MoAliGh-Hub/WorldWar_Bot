from flask import Flask, jsonify, request, render_template
import sqlite3
import time
import os

app = Flask(__name__)
DB_NAME = "world_war_game.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

init_db()

SUPERPOWERS = {
    "Russia": {"name": "روسیه", "pack": "پک اتمی تزار ☢️"},
    "USA": {"name": "آمریکا", "pack": "پک برتری هوایی ✈️"},
    "Iran": {"name": "ایران", "pack": "پک موشکی نقطه‌زن 🚀"},
    "UK": {"name": "انگلیس", "pack": "پک نیروی دریایی سلطنتی 🚢"},
    "France": {"name": "فرانسه", "pack": "پک زرهی زمینی 🎖"},
    "Israel": {"name": "اسرائیل", "pack": "پک جنگ سایبری و هکری 💻"},
    "China": {"name": "چین", "pack": "پک ساخت و ساز سریع 🏭"}
}

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
    last_collect = p[14]
    intervals = (now - last_collect) // 7200

    if intervals > 0:
        new_gold = p[5] + (intervals * p[9] * 500)
        new_iron = p[6] + (intervals * p[10] * 800)
        new_oil = p[7] + (intervals * p[11] * 1000)
        new_uranium = p[8] + (intervals * p[12] * 100)
        new_cash = p[4] + (intervals * p[13] * 200000)

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
        "cash": p[4],
        "gold": p[5],
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

@app.route('/api/build',methods=['POST'])
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

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
