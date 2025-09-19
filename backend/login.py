from multiprocessing.connection import wait
import os
import sys

from fastapi import FastAPI, Form, HTTPException, status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
from common import db_helpers
from fastapi import FastAPI, Request
from telegram import Update
from bot import telegram_app        # <-- Application instance from bot.py
from common.scraper import fetch_lpu_classes
from common.db_helpers import save_user, save_cookie

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
async def login_user(
    chat_id: int,
    username: str = Form(...),
    password_enc: str = Form(...)
):
    try:
        print(f"🔐 Login attempt for chat_id={chat_id}, username={username}")

        # This 'if' check is no longer needed because Form(...) makes the fields required.
        # FastAPI will automatically return a 422 error if they are missing.
        # if not username or not password_enc:
        #     return {"error": "Missing username or password"}

        # Save to Mongo
        await save_user(chat_id, username, password_enc)

        return {"status": "ok", "chat_id": chat_id}
    except Exception as e:
        # It's better practice to use HTTPException for specific error responses
        print(f"An internal error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred."
        )


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