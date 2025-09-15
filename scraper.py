import os
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


# ---------------------------
# Helpers
# ---------------------------
def get_user_credentials(chat_id: int):
    row = get_user(chat_id)
    if not row:
        raise RuntimeError("❌ No credentials found. Please login first.")
    username, password_enc, cookie, cookie_expiry = row
    password = decrypt_password(password_enc)
    return username, password, cookie, cookie_expiry


def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver_path = os.getenv("CHROMEDRIVER_PATH", ChromeDriverManager().install())
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=chrome_options)


# ---------------------------
# Cookie Login
# ---------------------------
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
        print("✅ Login successful:", driver.current_url)

        cookies = driver.get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        # Save with expiry (7 days)
        expiry_timestamp = int(time.time()) + (7 * 24 * 60 * 60)
        save_cookie(chat_id, cookie_str, expiry_timestamp)

        return cookie_str
    finally:
        driver.quit()


# ---------------------------
# Fetch Classes
# ---------------------------
def fetch_lpu_classes(chat_id: int, min_ts=None, max_ts=None):
    username, password, cookie, cookie_expiry = get_user_credentials(chat_id)

    # Check expiry
    now = int(time.time())
    if not cookie or not cookie_expiry or now > cookie_expiry:
        print("⚠️ Cookie expired or missing → Logging in again...")
        cookie = login_and_get_cookie(chat_id)

    if min_ts is None:
        min_ts = int(time.time() * 1000)
    if max_ts is None:
        max_ts = min_ts + 24 * 60 * 60 * 1000

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

    return r.json()


# ---------------------------
# Debug Utility
# ---------------------------
def print_classes(data):
    classes = data.get("ref") or data.get("data") or []
    if not classes:
        print("🎉 No upcoming classes found.")
        return

    for cls in classes:
        title = cls.get("title", "Unknown Class").strip()
        start = datetime.fromtimestamp(cls["startTime"] / 1000)
        end = datetime.fromtimestamp(cls["endTime"] / 1000)
        status = cls.get("status", "")

        print(f"📚 {title}")
        print(f"🕘 {start.strftime('%A, %d %B %Y %I:%M %p')} – {end.strftime('%I:%M %p')}")
        print(f"📌 Status: {status}")

        if cls.get("joinUrl"):
            print(f"🔗 Join: {cls['joinUrl']}")
        print("—" * 40)


if __name__ == "__main__":
    try:
        test_chat_id = 123456  # Replace with real chat_id for testing
        data = fetch_lpu_classes(test_chat_id)
        print_classes(data)
    except Exception as e:
        print("❌ Error:", e)
