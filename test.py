# local_scraper_run.py

import os
import time
import asyncio
import json
import ssl
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
from playwright.async_api import async_playwright

# --- Configuration & Constants ---
load_dotenv() # Load variables from .env file
LPU_API_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"
DUMMY_CHAT_ID = 12345  # A fake chat_id for local testing

# --- In-Memory Database Simulation ---
# This dictionary will act as our temporary database for a single run.
local_user_db = {
    DUMMY_CHAT_ID: {
        "chat_id": DUMMY_CHAT_ID,
        "username": os.getenv("LPU_USERNAME"),
        "password": os.getenv("LPU_PASSWORD"),
        "cookie": None,
        "cookie_expiry": None
    }
}

async def get_user(chat_id: int):
    """Mock DB helper: Fetches the user from our local dictionary."""
    print(f"[DB MOCK] Getting user {chat_id}")
    return local_user_db.get(chat_id)

async def save_cookie(chat_id: int, cookie: str, expiry_timestamp: float):
    """Mock DB helper: Saves a cookie to our local dictionary."""
    print(f"[DB MOCK] Saving cookie for user {chat_id}")
    if chat_id in local_user_db:
        local_user_db[chat_id]["cookie"] = cookie
        local_user_db[chat_id]["cookie_expiry"] = expiry_timestamp

# --- Scraper Logic (Adapted from your scraper.py) ---

async def playwright_login(username: str, password: str) -> tuple[str, int]:
    """Logs in using Playwright, bypassing SSL errors."""
    print(f"🚀 Performing Playwright login for user {username}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
                "--ignore-certificate-errors-spki-list", 
                "--disable-web-security"
            ]
        )
        context = await browser.new_context(ignore_https_errors=True)
        
        page = await context.new_page()
        await page.goto("https://myclass.lpu.in")
        await page.fill("input[name=i]", username)
        await page.fill("input[name=p]", password)
        await page.click("button:has-text('Login')")
        await page.wait_for_selector("#cssmenu", timeout=30000)
        print(f"✅ Playwright login successful for {username}")

        cookies = await context.cookies()
        await browser.close()
        
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60) # 7 days
        
        return cookie_str, expiry_timestamp

async def get_valid_cookie(chat_id: int, force_refresh: bool = False) -> str:
    """Gets a valid cookie from the DB or by performing a new login."""
    user = await get_user(chat_id)
    if not user:
        raise RuntimeError(f"No credentials found in DB for chat_id={chat_id}")

    cookie = user.get("cookie")
    cookie_expiry = user.get("cookie_expiry")

    if cookie and cookie_expiry and time.time() < cookie_expiry and not force_refresh:
        print(f"✅ Using cached cookie from DB for chat_id={chat_id}.")
        return cookie

    print(f"⚠️ Refreshing cookie for chat_id={chat_id}...")
    username = user.get("username")
    password = user.get("password")
    
    if not username or not password:
        raise RuntimeError("Missing username or password in DB.")

    new_cookie, new_expiry = await playwright_login(username, password)
    await save_cookie(chat_id, new_cookie, new_expiry)
    print(f"🍪 New cookie saved to DB for chat_id={chat_id}.")
    
    return new_cookie

async def fetch_lpu_classes(chat_id: int, min_ts=None, max_ts=None) -> dict:
    """Fetches classes for a given user, handling SSL verification securely with auto-retry."""
    if min_ts is None:
        min_ts = int(time.time() * 1000)
    if max_ts is None:
        max_ts = min_ts + 24 * 60 * 60 * 1000

    async def try_fetch(cookie: str):
        headers = {"Cookie": cookie, "Content-Type": "application/json"}
        payload = {
            "minDate": min_ts,
            "maxDate": max_ts,
            "filters": {"showSelf": True, "status": "started,scheduled,ended"}
        }
        ssl_context = ssl._create_unverified_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            print(f"📡 Fetching classes from API for chat_id={chat_id}...")
            async with session.post(LPU_API_URL, json=payload) as response:
                if response.status != 200:
                    raise RuntimeError(f"Fetch failed. Error {response.status}: {await response.text()}")
                if "application/json" not in response.headers.get("Content-Type", ""):
                    raise ValueError("Invalid cookie: server returned non-JSON response")
                return await response.json()

    try:
        cookie = await get_valid_cookie(chat_id)
        data = await try_fetch(cookie)
    except Exception as e:
        print(f"⚠️ Cookie expired or invalid. Retrying with fresh login... ({e})")
        cookie = await get_valid_cookie(chat_id, force_refresh=True)
        data = await try_fetch(cookie)

    classes = data.get("ref") or data.get("data") or []
    normalized = []

    # Normalize different class time formats into a standard 'startTime' and 'endTime'
    for cls in classes:
        if cls.get("startTime") and cls.get("endTime"):
            normalized.append(cls)
    
    return {"classes": normalized}


# --- Main Execution Block ---
async def main():
    """Main function to run the scraper locally."""
    print("--- Starting Local LPU Scraper Run ---")
    
    # Check if credentials are loaded
    if not local_user_db[DUMMY_CHAT_ID]["username"] or not local_user_db[DUMMY_CHAT_ID]["password"]:
        print("\n❌ ERROR: LPU_USERNAME or LPU_PASSWORD not found in .env file.")
        print("Please create a .env file with your credentials.")
        return

    try:
        # Fetch classes for the next 24 hours
        result = await fetch_lpu_classes(DUMMY_CHAT_ID)
        
        print("\n--- ✅ Scraper Finished Successfully ---")
        print(f"Found {len(result.get('classes', []))} classes for the next 24 hours.")
        
        # Pretty-print the JSON result
        print("\n--- Full Class Data ---")
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"\n--- ❌ An Error Occurred ---")
        print(f"Error: {e}")
        print("Please check your credentials in the .env file and ensure you can log in to myclass.lpu.in manually.")

if __name__ == "__main__":
    asyncio.run(main())