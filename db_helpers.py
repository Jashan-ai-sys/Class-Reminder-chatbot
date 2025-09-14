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
  # db_helper.py

def init_db():
    """Initializes the database, creating necessary indexes."""
    # This prevents duplicate users and makes lookups faster
    users_col.create_index("chat_id", unique=True)
    print("Database initialized and indexes ensured.")

# You can define a generic update function if you need it
def update_user(chat_id, data: dict):
    """Updates a user document with the given data."""
    users_col.update_one(
        {"chat_id": chat_id},
        {"$set": data},
        upsert=True
    )
