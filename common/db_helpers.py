# In common/db_helpers.py

import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime

# Define global variables, but leave them empty until init_db() is called.
client = None
db = None
users_col = None

def init_db():
    """
    Initializes the database connection and sets up the collections.
    This should be called once when the application starts.
    """
    global client, db, users_col
    MONGO_URI = os.getenv("MONGO_URI")

    if not MONGO_URI:
        print("❌ FATAL ERROR: MONGO_URI environment variable is not set.")
        return

    try:
        # Establish the connection
        client = MongoClient(MONGO_URI)
        client.admin.command('ismaster') # A cheap command to verify the connection
        
        # Use one consistent database and collection name
        db = client['lpu_bot_db'] 
        users_col = db['users']
        
        print("✅ MongoDB connection successful.")
        
        # Optional: Create an index for faster lookups
        users_col.create_index("chat_id", unique=True)

    except ConnectionFailure as e:
        client = None # Reset on failure
        print(f"❌ FATAL ERROR: Could not connect to MongoDB. Error: {e}")
    except Exception as e:
        client = None # Reset on failure
        print(f"❌ An unexpected error occurred during DB initialization: {e}")

def get_user(chat_id: int):
    """Fetches a user by their integer chat_id."""
    if not users_col:
        print("⚠️ DB not connected. Cannot get user.")
        return None
    return users_col.find_one({"chat_id": chat_id})

def save_user(chat_id: int, username: str, password_enc: str):
    """Saves or updates user credentials using an integer chat_id."""
    if not users_col:
        print("⚠️ DB not connected. Cannot save user.")
        return
        
    users_col.update_one(
        {"chat_id": chat_id},  # Use integer for consistency
        {"$set": {
            "username": username, 
            "password": password_enc, 
            "updated_at": datetime.now()
        }},
        upsert=True
    )
    print(f"✅ User data saved for chat_id: {chat_id}")

def save_cookie(chat_id: int, cookie: dict, expiry_timestamp: float):
    """Save session cookie for a user."""
    if not users_col:
        print("⚠️ DB not connected. Cannot save cookie.")
        return
        
    users_col.update_one(
        {"chat_id": chat_id},  # Use integer
        {"$set": {"cookie": cookie, "cookie_expiry": expiry_timestamp}},
        upsert=True
    )

def set_reminder_preference(chat_id: int, minutes: int):
    """Saves the user's preferred reminder time in minutes."""
    if not users_col:
        print("⚠️ DB not connected. Cannot set reminder preference.")
        return

    users_col.update_one(
        {'chat_id': chat_id}, # Use integer
        {'$set': {'reminder_minutes': minutes}},
        upsert=True
    )
    print(f"✅ Reminder preference for {chat_id} set to {minutes} minutes.")

def get_reminder_preference(chat_id: int) -> int:
    """Gets the user's preferred reminder time. Defaults to 10 minutes."""
    if not users_col:
        print("⚠️ DB not connected. Using default reminder time.")
        return 10  # Default value

    user = users_col.find_one({'chat_id': chat_id}) # Use integer
    return user.get('reminder_minutes', 10) if user else 10