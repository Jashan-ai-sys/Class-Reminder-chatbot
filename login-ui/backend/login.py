from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from db_helpers import save_user
from crypto import encrypt_password
import os

app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://your-frontend.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login/{chat_id}")
async def login_submit(
    chat_id: str,
    username: str = Form(...),
    password: str = Form(...),
   
):
    enc_pass = encrypt_password(password)
    save_user(chat_id, username, enc_pass)
    # 🚀 Automatically trigger reminders after login
    try:
        # run reminder task in the telegram bot’s job queue
        application.job_queue.run_once(
            lambda ctx: application.create_task(schedule_reminders(int(chat_id))),
            when=1  # start after 1 second
        )
    except Exception as e:
        print(f"⚠️ Could not schedule reminders: {e}")
        
    return {"status": "success"}

@app.get("/test")
async def test():
    return {"status": "ok", "message": "🚀 Backend is running fine on Railway!"}
