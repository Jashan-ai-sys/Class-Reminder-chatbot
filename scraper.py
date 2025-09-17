import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import pymongo
import urllib3

# Disable SSL warnings (Codetantra sometimes gives cert issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------
# Load ENV
# ------------------------
load_dotenv()

URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"
USERNAME = os.getenv("LPU_USERNAME")
PASSWORD = os.getenv("LPU_PASSWORD")
MONGO_URI = os.getenv("MONGO_URI", "")

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ Please set LPU_USERNAME and LPU_PASSWORD in .env file")

# ------------------------
# MongoDB Setup
# ------------------------
mongo_client = pymongo.MongoClient(MONGO_URI) if MONGO_URI else None
db = mongo_client["lpu_bot"] if mongo_client else None
cookies_col = db["cookies"] if db else None

# ------------------------
# Login & Get Cookie
# ------------------------
def playwright_login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://myclass.lpu.in")
        page.fill("input[name=i]", USERNAME)
        page.fill("input[name=p]", PASSWORD)
        page.click("button:has-text('Login')")
        page.wait_for_selector("#cssmenu", timeout=30000)

        print(f"✅ Login successful for {USERNAME}: {page.url}")

        cookies = page.context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        browser.close()

        expiry = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days
        return cookie_str, expiry

# ------------------------
# Cookie Manager
# ------------------------
def get_cookie():
    if not cookies_col:
        # fallback to always login
        return playwright_login()[0]

    row = cookies_col.find_one({"username": USERNAME})
    now = int(time.time())

    if row and row.get("cookie") and row.get("expiry", 0) > now:
        return row["cookie"]

    cookie, expiry = playwright_login()
    cookies_col.update_one(
        {"username": USERNAME},
        {"$set": {"cookie": cookie, "expiry": expiry}},
        upsert=True
    )
    return cookie

# ------------------------
# Fetch Classes
# ------------------------
def fetch_lpu_classes(min_ts=None, max_ts=None):
    if min_ts is None:
        min_ts = int(time.time() * 1000)
    if max_ts is None:
        max_ts = min_ts + 24 * 60 * 60 * 1000

    cookie = get_cookie()

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

    r = requests.post(URL, headers=headers, json=payload, verify=False)
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
# Print Classes
# ------------------------
def print_classes(data):
    classes = data.get("classes", [])
    if not classes:
        print("🎉 No upcoming classes found.")
        return

    for cls in classes:
        title = cls.get("title", "Unknown Class").strip()
        start = datetime.fromtimestamp(cls["startTime"] / 1000)
        end = datetime.fromtimestamp(cls["endTime"] / 1000)
        print(f"📚 {title}")
        print(f"🕘 {start:%A, %d %B %Y %I:%M %p} – {end:%I:%M %p}")
        print(f"📌 {cls.get('status','')}")
        print("—" * 40)

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    try:
        data = fetch_lpu_classes()
        print_classes(data)
    except Exception as e:
        print("❌ Error:", e)
