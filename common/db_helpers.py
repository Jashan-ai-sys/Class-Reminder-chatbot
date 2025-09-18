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
    if not user:
        return None
    return {
        "chat_id": user.get("chat_id"),
        "username": user.get("username"),
        "password": user.get("password"),
    }




def get_user_by_chat_id(chat_id: int):
    return users_col.find_one({"chat_id": str(chat_id)})
def save_cookie(chat_id, cookie, expiry_timestamp):
    """Save session cookie for a user."""
    users_col.update_one(
        {"chat_id": str(chat_id)},
        {"$set": {"cookie": cookie, "cookie_expiry": expiry_timestamp}},
        upsert=True
    )
def init_db():
    """Initialize MongoDB collections and indexes if needed."""
    # ensure chat_id is indexed/unique
    try:
        users_col.create_index("chat_id", unique=True)
    except Exception as e:
        print(f"[WARN] Could not create index on chat_id: {e}")
# In common/db_helpers.py

def set_reminder_preference(chat_id: int, minutes: int):
    """Saves the user's preferred reminder time in minutes."""
    if not client:
        print("⚠️ DB not connected. Cannot set reminder preference.")
        return

    try:
        db = client['lpu_bot_db']
        users = db['users']
        users.update_one(
            {'chat_id': chat_id},
            {'$set': {'reminder_minutes': minutes}},
            upsert=True  # Ensure user document is created if it doesn't exist
        )
        print(f"✅ Reminder preference for {chat_id} set to {minutes} minutes.")
    except Exception as e:
        print(f"❌ Error setting reminder preference for {chat_id}: {e}")

def get_reminder_preference(chat_id: int) -> int:
    """Gets the user's preferred reminder time. Defaults to 10 minutes."""
    if not client:
        print("⚠️ DB not connected. Using default reminder time.")
        return 10  # Default value

    db = client['lpu_bot_db']
    users = db['users']
    user = users.find_one({'chat_id': chat_id})

    # Return the user's preference, or 10 if it's not set
    return user.get('reminder_minutes', 10) if user else 10