from multiprocessing.connection import wait
import os
import sys
from common.playwright_manager import close_browser

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
from common import db_helpers
from fastapi import FastAPI, Request
from telegram import Update
from bot import telegram_app        # <-- Application instance from bot.py
from common.scraper import fetch_lpu_classes
from common.db_helpers import save_user, save_cookie
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.middleware.cors import CORSMiddleware
from telegram.error import RetryAfter
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root route for health checks
@app.get("/")
async def root():
    return {"status": "ok", "message": "Service is running"}

# ✅ Login route (frontend will call this)
@app.post("/login/{chat_id}")
async def login_user(chat_id: int, request: Request):
    try:
        body = await request.json()
        username = body.get("username")
        password_enc = body.get("password")
        print(f"🔐 Login attempt for chat_id={chat_id}, username={username}")
        if not username or not password_enc:
            return {"error": "Missing username or password"}

        # Save to Mongo
        await save_user(chat_id, username, password_enc)

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
    await db_helpers.init_db()
    from bot import main, telegram_app
    from common.reminders import check_classes_and_send_reminders
    
    # Initialize bot
    main() # Call main() to register handlers
    await telegram_app.initialize()
    await telegram_app.start()

    # Set Webhook with Retry Logic
    from bot import APP_URL
    
    if APP_URL:
        webhook_url = f"{APP_URL}/superSecretBotPath734hjw"
        print(f"🚀 Setting webhook to: {webhook_url}")
        
        for attempt in range(3):
            try:
                await telegram_app.bot.set_webhook(url=webhook_url)
                print("✅ Webhook set successfully.")
                break
            except RetryAfter as e:
                print(f"⚠️ Flood control exceeded. Retrying in {e.retry_after} seconds...")
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                print(f"❌ Failed to set webhook: {e}")
                break
    else:
        print("⚠️ APP_URL not set. Webhook not configured.")

    # Start the reminder scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_classes_and_send_reminders, "interval", seconds=60, args=[telegram_app]
    )
    scheduler.start()
    print("⏰ Reminder scheduler started (checks every 60s).")

@app.on_event("shutdown")
async def shutdown_event():
    await close_browser()
    # await telegram_app.stop() # Good practice to stop the bot app too
    # await telegram_app.shutdown()

@app.post("/superSecretBotPath734hjw")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("🚀 Webhook called with:", data)
    print("➡️ Passing update to telegram_app.process_update...")
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    print("✅ Update processed")
    return {"ok": True}