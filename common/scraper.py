# common/scraper.py
import os
import time
import aiohttp
import ssl
import certifi
from playwright.async_api import async_playwright

# Import the database helpers
from .db_helpers import get_user, save_cookie

LPU_API_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"
semaphore = asyncio.Semaphore(2) 
async def playwright_login(username: str, password: str) -> tuple[str, int]:
    """Logs in using Playwright, bypassing SSL errors."""
    print(f"🚀 Performing Playwright login for user {username}...")
    async with async_playwright() as p:
        # FIX #1: Pass launch arguments to Chromium to ignore certificate errors
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
        # Also set the context to ignore errors for good measure
        context = await browser.new_context(ignore_https_errors=True)
        
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
        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60) # 7 days
        
        return cookie_str, expiry_timestamp

async def get_valid_cookie(chat_id: int, force_refresh: bool = False) -> str:
    """Gets a valid cookie from the DB or by performing a new login."""
    user = await get_user(chat_id)
    if not user:
        raise RuntimeError(f"No credentials found in DB for chat_id={chat_id}")

    cookie = user.get("cookie")
    cookie_expiry = user.get("cookie_expiry")

    # Only use cached cookie if still valid & not forcing refresh
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

async def fetch_lpu_classes(chat_id: int):
    """Fetch and cache class schedule for user (uses Playwright tabs)."""

    # 1. Check cache first
    cached = await db_helpers.get_cached_schedule(chat_id)
    if cached and cached["expiry"] > datetime.now(IST):
        return cached["data"]

    # 2. Otherwise, scrape fresh
    async def scrape_classes(page, chat_id):
        # --- your login logic here ---
        await page.goto("https://lpulive.lpu.in")   # example
        # TODO: login with cookie or username/password
        # TODO: navigate and fetch timetable data

        # Example dummy output
        return {"classes": []}

    data = await run_in_tab(scrape_classes, chat_id)

    # 3. Cache results in DB for 3 hours
    await db_helpers.save_cached_schedule(
        chat_id,
        {"data": data, "expiry": datetime.now(IST) + timedelta(hours=3)}
    )
