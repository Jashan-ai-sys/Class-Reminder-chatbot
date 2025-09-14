from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "lpu_bot")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db["users"]

def save_user(chat_id, username, password_enc):
    users_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"username": username, "password": password_enc}},
        upsert=True
    )

def save_cookie(chat_id, cookie: str, expiry: int):
    users_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"cookie": cookie, "cookie_expiry": expiry}},
        upsert=True
    )

def get_user(chat_id):
    user = users_col.find_one({"chat_id": chat_id})
    if not user:
        return None
    return (
        user.get("username"),
        user.get("password"),
        user.get("cookie"),
        user.get("cookie_expiry"),
    )
