import os
from motor.motor_asyncio import AsyncIOMotorClient # Use the ASYNC motor driver
from pymongo.errors import ConnectionFailure
from datetime import datetime

# Define global variables, to be initialized by init_db()
client = None
db = None
users_col = None

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

async def init_db():
    """Initializes and actively tests the async database connection."""
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
    # This is the corrected check
    if users_col is None:
        print("⚠️ DB not connected. Cannot get user.")
        return None
    return await users_col.find_one({"chat_id": chat_id})

async def save_user(chat_id: int, username: str, password_enc: str):
    """Saves or updates user credentials asynchronously."""
    if users_col is None: return
    
    await users_col.update_one(
        {"chat_id": chat_id},
        {"$set": { "username": username, "password": password_enc, "updated_at": datetime.now() }},
        upsert=True
    )
    print(f"✅ User data saved for chat_id: {chat_id}")




def get_user_by_chat_id(chat_id: int):
    return users_col.find_one({"chat_id": str(chat_id)})
def save_cookie(chat_id, cookie, expiry_timestamp):
    """Save session cookie for a user."""
    users_col.update_one(
        {"chat_id": str(chat_id)},
        {"$set": {"cookie": cookie, "cookie_expiry": expiry_timestamp}},
        upsert=True
    )


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