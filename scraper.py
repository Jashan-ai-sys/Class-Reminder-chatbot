import os
import string
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from db_helpers import get_user, save_cookie
from crypto import decrypt_password

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/rest/dd/mf"


# ------------------------
# Get credentials from DB
# ------------------------
def get_user_credentials(chat_id: string):
    """
    Returns (username, decrypted_password, cookie, cookie_expiry) for a user.
    """
    row = get_user(chat_id)
    if not row:
        raise RuntimeError("❌ No credentials found. Please login first.")

    username, password_enc, cookie, cookie_expiry = row
    password = decrypt_password(password_enc)
    return username, password, cookie, cookie_expiry


# ------------------------
# Chrome driver (headless)
# ------------------------
def get_chrome_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


# ------------------------
# Login & Save Cookie
# ------------------------
def login_and_get_cookie(chat_id: int):
    username, password, _, _ = get_user_credentials(chat_id)
    driver = get_chrome_driver()

    try:
        driver.get("https://myclass.lpu.in")

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "i")))
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "p")))

        driver.find_element(By.NAME, "i").send_keys(username)
        driver.find_element(By.NAME, "p").send_keys(password)
        driver.find_element(By.XPATH, "//button[contains(text(),'Login')]").click()

        WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, "cssmenu")))
        print(f"✅ Login successful for {username}: {driver.current_url}")

        cookies = driver.get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60)
        save_cookie(chat_id, cookie_str, expiry_timestamp)

        return cookie_str
    finally:
        driver.quit()


# ------------------------
# Fetch Classes
# ------------------------
def fetch_lpu_classes(chat_id: int, min_ts=None, max_ts=None):
    _, _, cookie, cookie_expiry = get_user_credentials(chat_id)

    if min_ts is None:
        min_ts = int(time.time() * 1000)
    if max_ts is None:
        max_ts = min_ts + 24 * 60 * 60 * 1000

    if not cookie or (cookie_expiry and cookie_expiry < time.time()):
        cookie = login_and_get_cookie(chat_id)

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

    # Normalize to have startTime/endTime
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
# Print Classes (for debug)
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
# Standalone Test
# ------------------------
if __name__ == "__main__":
    test_chat_id = int(os.getenv("TEST_CHAT_ID", "123456"))
    try:
        data = fetch_lpu_classes(test_chat_id)
        print_classes(data)
    except Exception as e:
        print("❌ Error:", e)
