# In common/scraper.py

import os
import time
import aiohttp  # Use the async HTTP client
import asyncio  # Needed for the test runner
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

# Import the async helper functions from your corrected db_helpers.py
from .db_helpers import get_user, save_cookie
from .crypto import decrypt_password

URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"

async def get_user_credentials(chat_id: int):
    """Gets user credentials asynchronously from the database."""
    row = await get_user(chat_id)
    if not row:
        raise RuntimeError(f"❌ No credentials found for chat_id={chat_id}")

    username = row.get("username")
    password_enc = row.get("password")
    if not username or not password_enc:
        raise RuntimeError("❌ Missing username or password in DB")

    password = decrypt_password(password_enc)
    cookie = row.get("cookie")
    cookie_expiry = row.get("cookie_expiry")
    return username, password, cookie, cookie_expiry

async def playwright_login(username, password):
    """Logs in using Playwright to get a session cookie."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
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

async def get_valid_cookie(chat_id: int):
    """Reuses a saved cookie or logs in to get a new one."""
    username, password, cookie, cookie_expiry = await get_user_credentials(chat_id)

    if cookie and cookie_expiry and cookie_expiry > time.time():
        print("✅ Using saved, valid cookie.")
        return cookie

    print("🔄 Cookie expired or missing. Logging in again with Playwright…")
    new_cookie, expiry = await playwright_login(username, password)
    await save_cookie(chat_id, new_cookie, expiry)
    return new_cookie

async def fetch_lpu_classes(chat_id: int, min_ts=None, max_ts=None):
    """Fetches classes from the LPU API asynchronously."""
    if min_ts is None: min_ts = int(time.time() * 1000)
    if max_ts is None: max_ts = min_ts + 24 * 60 * 60 * 1000

    cookie = await get_valid_cookie(chat_id)
    headers = {"Cookie": cookie, "Content-Type": "application/json"}
    payload = {"minDate": min_ts, "maxDate": max_ts, "filters": {"showSelf": True, "status": "started,scheduled"}}

    # --- THIS IS THE CORRECTED ASYNC CODE ---
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(URL, json=payload) as response:
            if response.status != 200:
                raise RuntimeError(f"Fetch failed {response.status}: {await response.text()}")
            data = await response.json()
    # -----------------------------------------

    classes = data.get("ref") or data.get("data") or []
    # Your normalization logic is fine and can remain here
    # ...
    return {"classes": classes}

# --- This test runner is now corrected to work with async ---
async def main_test():
    """Wrapper function for async testing."""
    # Make sure to set TEST_CHAT_ID in your .env file for this to work
    chat_id = int(os.getenv("TEST_CHAT_ID", "123456"))
    try:
        # We need to initialize the DB for the test to work
        from common.db_helpers import init_db
        await init_db()
        
        data = await fetch_lpu_classes(chat_id)
        print("Test fetch successful. Data:", data)
    except Exception as e:
        print("❌ Test Error:", e)

if __name__ == "__main__":
    # Use asyncio.run to execute the async test function
    asyncio.run(main_test())