# common/scraper.py
import os
import time
import aiohttp
import ssl
import certifi
from playwright.async_api import async_playwright
from playwright_manager import run_in_tab 

# Import the database helpers
from .db_helpers import get_user, save_cookie

LPU_API_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"

async def playwright_login(username: str, password: str) -> tuple[str, int]:
    """Logs in using Playwright via manager, bypassing SSL errors."""

    async def _login_task(page):
        print(f"🚀 Performing Playwright login for user {username}...")

        # Block heavy assets
        await page.route("**/*.{png,jpg,jpeg,svg,woff,ttf}", lambda route: route.abort())
        await page.goto("https://myclass.lpu.in")

        await page.fill("input[name=i]", username)
        await page.fill("input[name=p]", password)
        await page.click("button:has-text('Login')")

        # Wait until dashboard is loaded
        await page.wait_for_selector("#cssmenu", timeout=30000)
        print(f"✅ Playwright login successful for {username}")

        cookies = await page.context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days

        return cookie_str, expiry_timestamp

    # Run the login inside the managed browser/tab
    return await run_in_tab(_login_task)


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

                # 👀 check for invalid cookie case
                if "application/json" not in response.headers.get("Content-Type", ""):
                    raise ValueError("Invalid cookie: server returned non-JSON response")

                return await response.json()

    try:
        # 1st attempt with cached cookie
        cookie = await get_valid_cookie(chat_id)
        data = await try_fetch(cookie)
    except Exception as e:
        print(f"⚠️ Cookie expired or invalid. Retrying with fresh login... ({e})")
        # 2nd attempt with force refresh
        cookie = await get_valid_cookie(chat_id, force_refresh=True)
        data = await try_fetch(cookie)

    # ✅ Normalize classes
    classes = data.get("ref") or data.get("data") or []
    normalized = []

    for cls in classes:
        # Case 1: recurring slots
        slots = cls.get("extra", {}).get("recurrence", {}).get("slots", [])
        if slots:
            for slot in slots:
                new_cls = cls.copy()
                new_cls["startTime"] = slot.get("start")
                new_cls["endTime"] = slot.get("end")
                new_cls["status"] = slot.get("status", cls.get("status", ""))
                normalized.append(new_cls)

        # Case 2: relative times
        elif cls.get("scheduledStartDayTime") and cls.get("scheduledEndDayTime"):
            base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start = int(base.timestamp() * 1000) + cls["scheduledStartDayTime"]
            end = int(base.timestamp() * 1000) + cls["scheduledEndDayTime"]

            new_cls = cls.copy()
            new_cls["startTime"] = start
            new_cls["endTime"] = end
            normalized.append(new_cls)

        # Case 3: already has absolute times
        elif cls.get("startTime") and cls.get("endTime"):
            normalized.append(cls)

    return {"classes": normalized}
