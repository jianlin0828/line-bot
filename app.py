import os
import sqlite3
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    TemplateSendMessage, CarouselTemplate, CarouselColumn, MessageAction
)
from dotenv import load_dotenv
from datetime import datetime

# Load .env config
load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# Flask app
app = Flask(__name__)

# Database init
DB_FILE = 'record.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                name TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                today INTEGER NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        conn.commit()

def get_record(name):
    today_str = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, total, today, date FROM records WHERE name=?", (name,))
        row = cursor.fetchone()
        if row:
            if row[3] != today_str:
                return (row[0], row[1], 0, today_str)  # reset today's value if date not match
            return row
        else:
            return (name, 0, 0, today_str)

def update_record(name, total, today, date):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO records (name, total, today, date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET total=?, today=?, date=?
        ''', (name, total, today, date, total, today, date))
        conn.commit()

def get_all_records():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, total, today FROM records")
        return cursor.fetchall()

# Initialize DB
init_db()

# LINE Callback route
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("錯誤：", e)
        return "Internal Server Error", 500
    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    
    if text == "/罰款":
        members = ["uj", "建霖", "聖宗", "勾八", "小麻", "小蘋果", "冠珉"]
        columns = []
        group_size = 3
        for i in range(0, len(members), group_size):
            group = members[i:i+group_size]
            while len(group) < group_size:
                group.append("無")
            actions = [MessageAction(label=name, text=f"/記錄 {name}") for name in group]
            columns.append(CarouselColumn(title="記錄罰款", text="請點選講出禁詞的人", actions=actions))
        carousel = TemplateSendMessage(alt_text='誰講了禁詞？', template=CarouselTemplate(columns=columns))
        line_bot_api.reply_message(event.reply_token, carousel)

    elif text.startswith("/記錄"):
        name = text.replace("/記錄 ", "")
        name, total, today, date = get_record(name)
        if today >= 50:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"{name} 今天已經罰滿 50 元了，不能再罰囉 ❌"))
        else:
            total += 10
            today += 10
            update_record(name, total, today, date)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"{name} 被罰 10 元！\n今日罰款：{today} 元 / 50 元\n總罰款：{total} 元")
            )

    elif text.startswith("/扣除"):
        try:
            parts = text.strip().split()
            if len(parts) != 3:
                raise ValueError("請輸入：/扣除 [名字] [金額]")
            name = parts[1]
            amount = int(parts[2])
            name, total, today, date = get_record(name)
            total = max(0, total - amount)
            update_record(name, total, today, date)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"{name} 扣除 {amount} 元罰款，目前剩下 {total} 元 💸"))
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="格式錯誤，請用：/扣除 [名字] [金額]  例如：/扣除 小麻 10"))

    elif text == "/排行榜":
        records = get_all_records()
        if not records:
            msg = "目前沒有任何罰款紀錄 ✅"
        else:
            msg = "目前罰款排行榜：\n"
            for name, total, today in records:
                msg += f"{name}: 總共 {total} 元，今天 {today} 元\n"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

if __name__ == "__main__":
    app.run(port=5000)
