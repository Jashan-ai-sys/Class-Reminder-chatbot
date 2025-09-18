import os
import time
from fastapi import FastAPI, Request
from telegram import Update
from bot import telegram_app        # <-- Application instance from bot.py
from scraper import fetch_lpu_classes
from db_helpers import save_user, save_cookie

app = FastAPI()

# Same webhook path you used in bot.py
WEBHOOK_PATH = "/superSecretBotPath734hjw"


# ✅ Telegram Webhook
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


# ✅ Login route (frontend will call this)
@app.post("/login/{chat_id}")
async def login_user(chat_id: int, request: Request):
    try:
        body = await request.json()
        username = body.get("username")
        password_enc = body.get("password")

        if not username or not password_enc:
            return {"error": "Missing username or password"}

        # Save to Mongo
        save_user(chat_id, username, password_enc)

        return {"status": "ok", "chat_id": chat_id}
    except Exception as e:
        return {"error": str(e)}


# ✅ Schedule fetch route
@app.post("/schedule/{chat_id}")
async def get_schedule(chat_id: int):
    try:
        data = await fetch_lpu_classes(chat_id)
        return data
    except Exception as e:
        return {"error": str(e)}
