# In common/db_helpers.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from cryptography.fernet import Fernet  # <-- ADDED

# Define global variables, to be initialized by init_db()
client = None
db = None
users_col = None
cipher_suite = None  # <-- ADDED: To hold the encryption tool

async def init_db():
    """
    Initializes the database connection and the encryption service.
    """
    global client, db, users_col, cipher_suite  # <-- MODIFIED
    MONGO_URI = os.getenv("MONGO_URI")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # <-- ADDED

    if not MONGO_URI or not ENCRYPTION_KEY:  # <-- MODIFIED
        print("❌ FATAL ERROR: MONGO_URI or ENCRYPTION_KEY environment variable is not set.")
        return

    try:
        # Initialize the encryption cipher
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())  # <-- ADDED
        print("✅ Encryption service initialized.")
        
        print("Connecting to MongoDB...")
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        
        db = client['lpu_bot_db']
        users_col = db['users']
        
        print("✅ MongoDB connection successful.")
        
    except Exception as e:
        client = None
        cipher_suite = None
        print(f"❌ FATAL ERROR: Could not initialize services. Error: {e}")

# Encryption and Decryption Helper Functions --- START --- (all new)

def encrypt_password(password: str) -> str:
    """Encrypts a password string."""
    if cipher_suite is None:
        raise Exception("Cipher not initialized")
    encrypted_bytes = cipher_suite.encrypt(password.encode())
    return encrypted_bytes.decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypts a password string."""
    if cipher_suite is None:
        raise Exception("Cipher not initialized")
    try:
        decrypted_bytes = cipher_suite.decrypt(encrypted_password.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        print(f"⚠️ Failed to decrypt password: {e}")
        return "" # Return empty or handle error as needed

# Encryption and Decryption Helper Functions --- END ---

async def get_user(chat_id: int):
    """Fetches a user and decrypts their password."""
    if users_col is None:
        print("⚠️ DB not connected. Cannot get user.")
        return None
        
    user = await users_col.find_one({"chat_id": chat_id})

    # <-- MODIFIED: Decrypt password after fetching
    if user and "password" in user:
        user["password"] = decrypt_password(user["password"])
        
    return user

async def save_user(chat_id: int, username: str, password_plain: str): # Renamed for clarity
    """Encrypts and saves user credentials asynchronously."""
    if users_col is None:
        print("⚠️ DB not connected. Cannot save user.")
        return
    
    # <-- MODIFIED: Encrypt password before saving
    encrypted_password = encrypt_password(password_plain)
        
    await users_col.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "username": username, 
            "password": encrypted_password, # Store the encrypted password
            "updated_at": datetime.now()
        }},
        upsert=True
    )
    print(f"✅ User data saved for chat_id: {chat_id}")

# --- No changes are needed for the functions below this line ---

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
    return user.get('reminder_minutes', 10) if user else 10