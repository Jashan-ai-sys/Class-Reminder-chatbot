from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from db_helpers import save_user
from crypto import encrypt_password
import os

app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://login-frontend-h8oi-mea5018wf-jashan-ai-sys-projects.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login")
async def login_submit(
    username: str = Form(...),
    password: str = Form(...),
   
):
    enc_pass = encrypt_password(password)
    save_user(username, enc_pass)
    return {"status": "success"}
@app.get("/test")
async def test():
    return {"status": "ok", "message": "🚀 Backend is running fine on Railway!"}