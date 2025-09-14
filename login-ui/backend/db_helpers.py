import os
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL")  # Railway env var
client = MongoClient(MONGO_URL)

db = client["lpu_bot"]   # Database
users_col = db["users"]  # Collection for users
reminders_col = db["reminders"]  # Collection for reminders

def save_user(username, password_enc):
    users_col.update_one(
        {"username": username},   # use username as unique key
        {"$set": {"username": username, "password": password_enc}},
        upsert=True
    )


def get_user(chat_id: str):
    return users_col.find_one({"chat_id": chat_id})

def delete_user(chat_id: str):
    users_col.delete_one({"chat_id": chat_id})
