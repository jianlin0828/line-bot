import os
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, MessageAction, CarouselTemplate, CarouselColumn
)
from dotenv import load_dotenv
from datetime import datetime

# 載入 .env 配置
load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 儲存罰款紀錄
record = {}

app = Flask(__name__)

recently_added = {}

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
        try:
            members = ["uj", "建霖", "聖宗", "勾八", "小麻", "小蘋果", '冠珉']
            columns = []

            # 每 3 人一組，不足補滿
            group_size = 3
            for i in range(0, len(members), group_size):
                group = members[i:i + group_size]
                while len(group) < group_size:
                    group.append("無")  # 補空人名避免錯誤

                actions = [
                    MessageAction(label=name, text=f"/記錄 {name}") for name in group
                ]
                column = CarouselColumn(
                    title="記錄罰款",
                    text="請點選講出禁詞的人",
                    actions=actions
                )
                columns.append(column)

            carousel = TemplateSendMessage(
                alt_text='誰講了禁詞？',
                template=CarouselTemplate(columns=columns)
            )
            line_bot_api.reply_message(event.reply_token, carousel)

        except Exception as e:
            print("傳送按鈕錯誤：", e)

    elif text.startswith("/記錄"):
        name = text.replace("/記錄 ", "")
        today_str = datetime.now().strftime("%Y-%m-%d")

        if name not in record:
            record[name] = {"total": 0, "today": 0, "date": today_str}

        # 檢查是否是新的一天
        if record[name]["date"] != today_str:
            record[name]["today"] = 0
            record[name]["date"] = today_str

        if record[name]["today"] >= 50:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"{name} 今天已經罰滿 50 元了，不能再罰囉 ❌")
            )
        else:
            record[name]["total"] += 10
            record[name]["today"] += 10
            recently_added[name] = 10  # 記錄這次的加金額
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"{name} 被罰 10 元！\n今日罰款：{record[name]['today']} 元 / 50 元\n總罰款：{record[name]['total']} 元")
            )

    elif text.startswith("/扣除"):
        try:
            parts = text.strip().split()
            if len(parts) != 3:
                raise ValueError("請輸入：/扣除 [名字] [金額]")

            name = parts[1]
            amount = int(parts[2])

            if name not in record:
                record[name] = {"total": 0, "today": 0, "date": datetime.now().strftime("%Y-%m-%d")}

            # 檢查是否為誤點操作（即同時有加10後扣除）
            if name in recently_added and recently_added[name] == amount:
                # 如果誤扣，恢復total和today
                record[name]["total"] -= amount
                record[name]["today"] -= amount
                recently_added.pop(name, None)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"誤扣操作，已恢復 {name} 的罰款！目前總罰款：{record[name]['total']} 元")
                )
            else:
                record[name]["total"] = max(0, record[name]["total"] - amount)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"{name} 扣除 {amount} 元罰款，目前剩下 {record[name]['total']} 元 💸")
                )
        except ValueError as ve:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=str(ve))
            )
        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤，請用：/扣除 [名字] [金額]  例如：/扣除 小麻 10")
            )

    elif text == "/排行榜":
        if not record:
            msg = "目前沒有任何罰款紀錄 ✅"
        else:
            msg = "目前罰款排行榜：\n"
            for name, data in record.items():
                msg += f"{name}: 總共 {data['total']} 元，今天 {data['today']} 元\n"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

if __name__ == "__main__":
    app.run(port=5000)
