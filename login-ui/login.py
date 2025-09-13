from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from db_helpers import save_user_credentials
from crypto import encrypt_password

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/login/{chat_id}", response_class=HTMLResponse)
async def login_form(request: Request, chat_id: str):
    return templates.TemplateResponse("login.html", {"request": request, "chat_id": chat_id})

@app.post("/login/{chat_id}", response_class=HTMLResponse)
async def login_submit(request: Request, chat_id: str, username: str = Form(...), password: str = Form(...)):
    save_user_credentials(chat_id, username, encrypt_password(password))
    return templates.TemplateResponse("success.html", {"request": request})
