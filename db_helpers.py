from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["lpu_bot"]
users_col = db["users"]

# Save only username + encrypted password
def save_user(chat_id, username, password_enc):
    users_col.update_one(
        {"chat_id": str(chat_id)},   # store as string
        {"$set": {"username": username, "password": password_enc, "chat_id": str(chat_id)}},
        upsert=True
    )

# Link Telegram chat_id later
def link_chat_id(username: str, chat_id: int):
    users_col.update_one(
        {"username": username},
        {"$set": {"chat_id": str(chat_id)}},
    )

def get_user(chat_id):
    user = users_col.find_one({"chat_id": str(chat_id)})
    print(f"[DEBUG] get_user({chat_id}) -> {user}")  # keep debug
    return user



def get_user_by_chat_id(chat_id: int):
    return users_col.find_one({"chat_id": str(chat_id)})
