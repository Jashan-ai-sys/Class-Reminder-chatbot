from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["lpu_bot"]
users_col = db["users"]

# Save only username + encrypted password
def save_user(username: str, password_enc: str):
    users_col.update_one(
        {"username": username},
        {"$set": {"username": username, "password": password_enc}},
        upsert=True,
    )

# Link Telegram chat_id later
def link_chat_id(username: str, chat_id: int):
    users_col.update_one(
        {"username": username},
        {"$set": {"chat_id": chat_id}},
    )

def get_user_by_username(username: str):
    return users_col.find_one({"username": username})

def get_user_by_chat_id(chat_id: int):
    return users_col.find_one({"chat_id": chat_id})
