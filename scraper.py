import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta

from db_helpers import get_user, save_cookie
from crypto import decrypt_password

load_dotenv()

URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"

# ------------------------
# Get credentials from Mongo
# ------------------------
def get_user_credentials(chat_id: str):
    row = get_user(chat_id)
    if not row:
        raise RuntimeError(f"❌ No credentials found in MongoDB for chat_id={chat_id}")

    username = row.get("username")
    password_enc = row.get("password")

    if not username or not password_enc:
        raise RuntimeError("❌ Missing username or password in DB")

    password = decrypt_password(password_enc)
    cookie = row.get("cookie")
    cookie_expiry = row.get("cookie_expiry")

    return username, password, cookie, cookie_expiry

# ------------------------
# Login with Playwright
# ------------------------
async def playwright_login(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://myclass.lpu.in")

        await page.fill("input[name=i]", username)
        await page.fill("input[name=p]", password)
        await page.click("button:has-text('Login')")

        await page.wait_for_selector("#cssmenu", timeout=30000)
        print(f"✅ Login successful for {username}: {page.url}")

        cookies = await context.cookies()
        await browser.close()

        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days

        return cookie_str, expiry_timestamp

# ------------------------
# Get valid cookie (reuse if not expired)
# ------------------------
async def get_valid_cookie(chat_id: int):
    username, password, cookie, cookie_expiry = get_user_credentials(chat_id)

    if cookie and cookie_expiry and cookie_expiry > time.time():
        print("✅ Using saved cookie")
        return cookie

    print("🔄 Logging in again…")
    new_cookie, expiry = await playwright_login(username, password)
    save_cookie(chat_id, new_cookie, expiry)
    return new_cookie


# ------------------------
# Fetch Classes
# ------------------------
async def fetch_lpu_classes(chat_id: int, min_ts=None, max_ts=None):
    if min_ts is None:
        min_ts = int(time.time() * 1000)
    if max_ts is None:
        max_ts = min_ts + 24 * 60 * 60 * 1000

    cookie = await get_valid_cookie(chat_id)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://lovelyprofessionaluniversity.codetantra.com/",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Cookie": cookie,
    }

    payload = {
        "minDate": min_ts,
        "maxDate": max_ts,
        "filters": {"showSelf": True, "status": "started,scheduled"},
    }

    r = requests.post(URL, headers=headers, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Fetch failed {r.status_code}: {r.text[:200]}")

    data = r.json()
    classes = data.get("ref") or data.get("data") or []

    normalized = []
    for cls in classes:
        slots = cls.get("extra", {}).get("recurrence", {}).get("slots", [])
        if slots:
            for slot in slots:
                new_cls = cls.copy()
                new_cls["startTime"] = slot["start"]
                new_cls["endTime"] = slot["end"]
                new_cls["status"] = slot.get("status", cls.get("status", ""))
                normalized.append(new_cls)
        elif cls.get("scheduledStartDayTime") and cls.get("scheduledEndDayTime"):
            base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start = base.timestamp() * 1000 + cls["scheduledStartDayTime"]
            end = base.timestamp() * 1000 + cls["scheduledEndDayTime"]
            new_cls = cls.copy()
            new_cls["startTime"] = start
            new_cls["endTime"] = end
            normalized.append(new_cls)

    return {"classes": normalized}

# ------------------------
# Print Classes (debug)
# ------------------------
IST = timezone(timedelta(hours=5, minutes=30))
def print_classes(data):
    classes = data.get("classes", [])
    if not classes:
        print("🎉 No upcoming classes found.")
        return

    for cls in classes:
        title = cls.get("title", "Unknown Class").strip()
        start = datetime.fromtimestamp(cls["startTime"] / 1000, tz=timezone.utc).astimezone(IST)
        end = datetime.fromtimestamp(cls["endTime"] / 1000, tz=timezone.utc).astimezone(IST)
        print(f"📚 {title}")
        print(f"🕘 {start:%A, %d %B %Y %I:%M %p} – {end:%I:%M %p}")
        print(f"📌 {cls.get('status','')}")
        print("—" * 40)

# ------------------------
# Standalone Test
# ------------------------
if __name__ == "__main__":
    chat_id = int(os.getenv("TEST_CHAT_ID", "123456"))
    try:
        data = fetch_lpu_classes(chat_id)
        print_classes(data)
    except Exception as e:
        print("❌ Error:", e)
