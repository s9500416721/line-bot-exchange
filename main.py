from flask import Flask, request
import requests
import schedule
import threading
import time
import json
import os

app = Flask(__name__)
CHANNEL_ACCESS_TOKEN = os.getenv("QmBNHfDbBB2vJXtCvJuaoL2/bKAruUiUTXMBxcwOLfPeah8ZZQbosU1O1Un932B+RyFcXv1zSTmqja/h4WcbYvxzHNXElKR8Xm52C8C4z4CIuYYKqonku9fvqAicGYsZgFwIwoyjVNZkvxDG3l5z0AdB04t89/1O/w1cDnyilFU=")
USER_ID = os.getenv("Uf02220479b60ce5aa9813ab3d643fa54")



# === 取得匯率（TWD 對 KRW 與 JPY） ===
def get_exchange_rate():
    url = "https://open.er-api.com/v6/latest/TWD"
    response = requests.get(url)
    data = response.json()

    if data["result"] != "success":
        raise Exception("匯率 API 回傳失敗")

    twd_to_krw = data["rates"]["KRW"]
    twd_to_jpy = data["rates"]["JPY"]

    # 12000日圓和119000韓元對應的台幣數量
    jpy_to_twd = 12000 / twd_to_jpy  # 12000日圓換台幣
    krw_to_twd = 119000 / twd_to_krw  # 119000韓元換台幣

    return twd_to_krw, twd_to_jpy, jpy_to_twd, krw_to_twd

# === 傳送 LINE 訊息（處理特殊字元） ===
def send_line_message(message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "to": USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)
        response.raise_for_status()
    except Exception as e:
        print(f"發送訊息錯誤: {e}")

# === 每日自動排程：10:00 傳匯率 ===
def schedule_job():
    try:
        krw, jpy, jpy_to_twd, krw_to_twd = get_exchange_rate()
        msg = f"📊 今日匯率（TWD 兌）：\n12000日圓 = {jpy_to_twd:.2f} 台幣\n119000韓元 = {krw_to_twd:.2f} 台幣"
    except Exception as e:
        msg = f"取得匯率失敗：{e}"
    send_line_message(msg)

schedule.every().day.at("10:00").do(schedule_job)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_schedule, daemon=True).start()

# === Webhook 處理 LINE 訊息 ===
@app.route("/", methods=["POST"])
def webhook():
    body = request.get_data(as_text=True)
    json_data = json.loads(body)
    print("Received event:", json.dumps(json_data, indent=2))

    try:
        event = json_data["events"][0]
        user_id = event["source"]["userId"]
        message = event["message"]["text"]

        if message.strip() == "匯率":
            try:
                krw, jpy, jpy_to_twd, krw_to_twd = get_exchange_rate()
                msg = f"📊 即時匯率（TWD 兌）：\n12000日圓 = {jpy_to_twd:.2f} 台幣\n119000韓元 = {krw_to_twd:.2f} 台幣"
            except Exception as e:
                msg = f"取得匯率失敗：{e}"
            send_line_message(msg)
    except Exception as e:
        print("Webhook 處理錯誤：", e)

    return "OK"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
