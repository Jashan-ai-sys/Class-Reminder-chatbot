from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["lpu_bot"]
users_col = db["users"]

# Save only username + encrypted password
def save_user(chat_id, username, password_enc):
    users_col.update_one(
        {"chat_id": str(chat_id)},
        {"$set": {"username": username, "password": password_enc}},
        upsert=True
    )

# Link Telegram chat_id later
def link_chat_id(username: str, chat_id: int):
    users_col.update_one(
        {"username": username},
        {"$set": {"chat_id": str(chat_id)}},
    )

def get_user(chat_id):
    # Try matching as string
    user = users_col.find_one({"chat_id": str(chat_id)})
    if not user:
        # Fallback: try int
        user = users_col.find_one({"chat_id": chat_id})

    if not user:
        return None

    return {
        "chat_id": str(user.get("chat_id")),
        "username": user.get("username"),
        "password": user.get("password")
    }



def get_user_by_chat_id(chat_id: int):
    return users_col.find_one({"chat_id": str(chat_id)})
