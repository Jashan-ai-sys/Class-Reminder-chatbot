# common/scraper.py
import os
import time
import aiohttp
from playwright.async_api import async_playwright

# Import the database helpers
from db_helpers import get_user, save_cookie

LPU_API_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"

async def playwright_login(username: str, password: str) -> tuple[str, int]:
    """Logs in using Playwright to get a new session cookie and expiry."""
    print(f"🚀 Performing Playwright login for user {username}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.route("**/*.{png,jpg,jpeg,svg,woff,ttf}", lambda route: route.abort())
        await page.goto("https://myclass.lpu.in")
        await page.fill("input[name=i]", username)
        await page.fill("input[name=p]", password)
        await page.click("button:has-text('Login')")
        await page.wait_for_selector("#cssmenu", timeout=30000)
        print(f"✅ Playwright login successful for {username}")

        cookies = await context.cookies()
        await browser.close()
        
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        # Set expiry for 7 days from now
        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60) 
        
        return cookie_str, expiry_timestamp

async def get_valid_cookie(chat_id: int) -> str:
    """
    Gets a valid cookie by checking the database first, 
    or by logging in to get a new one.
    """
    user = await get_user(chat_id)
    if not user:
        raise RuntimeError(f"❌ No credentials found in DB for chat_id={chat_id}")

    cookie = user.get("cookie")
    cookie_expiry = user.get("cookie_expiry")

    # Check if a valid, unexpired cookie exists in the database
    if cookie and cookie_expiry and time.time() < cookie_expiry:
        print(f"✅ Using cached cookie from DB for chat_id={chat_id}.")
        return cookie

    # If no valid cookie exists, perform a new login
    print(f"⚠️ Cookie missing or expired for chat_id={chat_id}. Performing new login.")
    username = user.get("username")
    password = user.get("password") # Assumes password is now decrypted by get_user
    
    if not username or not password:
        raise RuntimeError("❌ Missing username or password in DB.")

    new_cookie, new_expiry = await playwright_login(username, password)
    
    # Save the new cookie to the database for future use
    await save_cookie(chat_id, new_cookie, new_expiry)
    
    return new_cookie

async def fetch_lpu_classes(chat_id: int, min_ts=None, max_ts=None) -> dict:
    """Fetches classes for a given user identified by chat_id."""
    if min_ts is None: 
        min_ts = int(time.time() * 1000)
    if max_ts is None: 
        max_ts = min_ts + 24 * 60 * 60 * 1000

    cookie = await get_valid_cookie(chat_id)
    
    headers = {"Cookie": cookie, "Content-Type": "application/json"}
    payload = {
        "minDate": min_ts, 
        "maxDate": max_ts, 
        "filters": {"showSelf": True, "status": "started,scheduled"}
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print(f"📡 Fetching classes from API for chat_id={chat_id}...")
        async with session.post(LPU_API_URL, json=payload) as response:
            if response.status != 200:
                # If the cookie from the DB was invalid, we should still try to log in again next time.
                # For simplicity, we just raise an error here. A more advanced implementation
                # could delete the bad cookie and retry the whole process.
                error_text = await response.text()
                raise RuntimeError(f"Fetch failed (likely invalid cookie). Error: {response.status}: {error_text}")
            data = await response.json()

    classes = data.get("ref") or data.get("data") or []
    return {"classes": classes}