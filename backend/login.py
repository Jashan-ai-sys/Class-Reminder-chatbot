import os
import time
from fastapi import FastAPI, Request
from telegram import Update
from bot import telegram_app        # <-- Application instance from bot.py
from scraper import fetch_lpu_classes
from db_helpers import save_user, save_cookie

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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
@app.on_event("startup")
async def startup_event():
    from bot import main, telegram_app
    main() 
    await telegram_app.initialize()
    await telegram_app.start()

@app.on_event("shutdown")
async def shutdown_event():
    await telegram_app.stop()
    await telegram_app.shutdown()

@app.post("/superSecretBotPath734hjw")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("🚀 Webhook called with:", data)
    print("➡️ Passing update to telegram_app.process_update...")
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    print("✅ Update processed")
    return {"ok": True}