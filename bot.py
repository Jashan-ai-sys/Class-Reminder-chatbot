import os
import logging
from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from db_helpers import save_user
from crypto import encrypt_password

# ------------------------
# Logging
# ------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------
# FastAPI app
# ------------------------
app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://your-frontend.vercel.app")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/superSecretBotPath734hjw")
APP_URL = os.getenv("APP_URL")  # Railway public URL

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Telegram bot
# ------------------------
application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Use /login to link your account.")

application.add_handler(CommandHandler("start", start))

# ------------------------
# FastAPI Routes
# ------------------------
@app.post("/login")
async def login_submit(
    username: str = Form(...),
    password: str = Form(...),
    chat_id: str = Form(...)
):
    enc_pass = encrypt_password(password)
    save_user(chat_id, username, enc_pass)
    return {"status": "success"}

@app.get("/test")
async def test():
    return {"status": "ok", "message": "🚀 Backend + Bot are running on Railway!"}

# Telegram Webhook endpoint
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# ------------------------
# Startup
# ------------------------
@app.on_event("startup")
async def on_startup():
    webhook_url = f"{APP_URL}{WEBHOOK_PATH}"
    logger.info(f"🌍 Setting webhook: {webhook_url}")
    await application.bot.set_webhook(webhook_url)
