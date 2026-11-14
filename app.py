import os
import time
import threading
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, PushMessageRequest, ImageMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])
config = Configuration(access_token=os.environ["CHANNEL_ACCESS_TOKEN"])

# Renderで発行されるURLに合わせて環境変数 BASE_URL を設定します
BASE_URL = os.environ.get("BASE_URL", "https://example.onrender.com")
IMAGE_URL = f"{BASE_URL}/static/pic.jpg"

COUNT = 20        # 送る枚数
INTERVAL = 0.1    # 送信間隔(秒)。エラーが出たら大きくする
TRIGGER = "稲泉"   # このメッセージを受け取ったら送信開始


def make_img():
    return ImageMessage(original_content_url=IMAGE_URL,
                        preview_image_url=IMAGE_URL)


def send_sequence(reply_token, user_id):
    with ApiClient(config) as client:
        api = MessagingApi(client)
        # 1枚目はreply(通数を消費しない)
        api.reply_message(ReplyMessageRequest(
            reply_token=reply_token, messages=[make_img()]))
        # 2枚目以降はpush
        for _ in range(COUNT - 1):
            time.sleep(INTERVAL)
            try:
                api.push_message(PushMessageRequest(
                    to=user_id, messages=[make_img()]))
            except Exception as e:
                print("push失敗:", e)
                break


@app.get("/")
def index():
    return "OK"


@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event):
    if event.message.text == TRIGGER:
        threading.Thread(
            target=send_sequence,
            args=(event.reply_token, event.source.user_id),
            daemon=True,
        ).start()
