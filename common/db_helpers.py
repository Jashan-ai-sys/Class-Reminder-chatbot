# In common/db_helpers.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from common.crypto import decrypt_password,encrypt_password

# Define global variables, to be initialized by init_db()
client = None
db = None
users_col = None

async def init_db():
    """
    Initializes and actively tests the async database connection.
    This should be called once when the application starts up.
    """
    global client, db, users_col
    MONGO_URI = os.getenv("MONGO_URI")

    if not MONGO_URI:
        print("❌ FATAL ERROR: MONGO_URI environment variable is not set.")
        return

    try:
        print("Connecting to MongoDB...")
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping') # Actively test the connection
        
        db = client['lpu_bot_db']
        users_col = db['users']
        
        print("✅ MongoDB connection successful.")
        
    except Exception as e:
        client = None
        print(f"❌ FATAL ERROR: Could not connect to MongoDB. Error: {e}")

async def get_user(chat_id: int):
    """Fetches a user by their integer chat_id."""
    if users_col is None:
        print("⚠️ DB not connected. Cannot get user.")
        return None
    user=await users_col.find_one({"chat_id": chat_id})
    if user and "password" in user:
        user["password"] = decrypt_password(user["password"])
    return user

async def save_user(chat_id: int, username: str, password_enc: str):
    """Saves or updates user credentials asynchronously."""
    if users_col is None:
        print("⚠️ DB not connected. Cannot save user.")
        return
    password_enc = encrypt_password(password_enc)
    await users_col.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "username": username, 
            "password": password_enc, 
            "updated_at": datetime.now()
        }},
        upsert=True
    )
    print(f"✅ User data saved for chat_id: {chat_id}")

async def save_cookie(chat_id: int, cookie: str, expiry_timestamp: float):
    """Saves a session cookie for a user asynchronously."""
    if users_col is None:
        print("⚠️ DB not connected. Cannot save cookie.")
        return
        
    await users_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"cookie": cookie, "cookie_expiry": expiry_timestamp}},
        upsert=True
    )
    print(f"✅ Cookie saved for chat_id: {chat_id}")

async def set_reminder_preference(chat_id: int, minutes: int):
    """Saves the user's preferred reminder time asynchronously."""
    if users_col is None:
        print("⚠️ DB not connected. Cannot set reminder preference.")
        return

    await users_col.update_one(
        {'chat_id': chat_id},
        {'$set': {'reminder_minutes': minutes}},
        upsert=True
    )
    print(f"✅ Reminder preference for {chat_id} set to {minutes} minutes.")

async def get_reminder_preference(chat_id: int) -> int:
    """Gets the user's preferred reminder time asynchronously."""
    if users_col is None:
        print("⚠️ DB not connected. Using default reminder time.")
        return 10  # Default value

    user = await users_col.find_one({'chat_id': chat_id})
    return user.get('reminder_minutes', 10) if user else 0