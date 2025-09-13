import os
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import json

# Disable the insecure request warning that comes with verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION (Load from Environment Variables) ---
LPU_USERNAME = os.getenv("LPU_USERNAME")
LPU_PASSWORD = os.getenv("LPU_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- STATE FILE ---
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"

# --- LPU URLS ---
MYCLASS_HOME_URL = "https://myclass.lpu.in/"
LOGIN_PROCESS_URL = "https://lovelyprofessionaluniversity.codetantra.com/r/l/p"
SCHEDULE_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/tla/m.jsp"


def load_sent_notifications():
    if not os.path.exists(SENT_NOTIFICATIONS_FILE):
        return []
    try:
        with open(SENT_NOTIFICATIONS_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return []
            return data.get("sent_list", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_sent_notifications(sent_list):
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sent_list": sent_list,
    }
    with open(SENT_NOTIFICATIONS_FILE, "w") as f:
        json.dump(data, f)


def send_telegram_notification(message: str):
    if not all([BOT_TOKEN, CHAT_ID]):
        print("ERROR: Bot Token or Chat ID is not set.")
        return

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Notification sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification: {e}")


def scrape_and_check_reminders():
    if not all([LPU_USERNAME, LPU_PASSWORD, BOT_TOKEN, CHAT_ID]):
        print("FATAL ERROR: Environment variables are missing.")
        return

    try:
        sent_today = load_sent_notifications()

        with requests.Session() as session:
            # 1. Initialize session
            print("Initializing session at myclass.lpu.in...")
            session.get(MYCLASS_HOME_URL, verify=False)

            # 2. Authenticate via CodeTantra login page
            print("Authenticating via CodeTantra...")
            login_payload = {"i": LPU_USERNAME, "p": LPU_PASSWORD}
            login_response = session.post(
                LOGIN_PROCESS_URL, data=login_payload, verify=False, allow_redirects=False
            )

            print("Login status:", login_response.status_code)
            print("Login headers:", login_response.headers)

            if login_response.status_code in (302, 303):
                redirect_url = login_response.headers.get("Location", "")
                if not redirect_url.startswith("http"):
                    redirect_url = "https://lovelyprofessionaluniversity.codetantra.com" + redirect_url
                print(f"Following redirect to {redirect_url}")
                home_resp = session.get(redirect_url, verify=False)
                print("Home page status:", home_resp.status_code)
                print("Home page snippet:")
                print(home_resp.text[:500])  # Debug snippet

            # 3. Now fetch the schedule page
            print("Fetching schedule page...")
            schedule_response = session.get(SCHEDULE_URL, verify=False)

            if "My Schedule" not in schedule_response.text:
                raise Exception("Login or navigation to schedule page failed.")
            print("Successfully accessed schedule page.")

            # 4. Parse schedule
            soup = BeautifulSoup(schedule_response.text, "html.parser")
            event_contents = soup.find_all("div", class_="fc-content")

            if not event_contents:
                print("No class events found on the schedule page.")
                return

            for content in event_contents:
                time_element = content.find("div", class_="fc-time")
                title_element = content.find("div", class_="fc-title")

                if time_element and title_element:
                    time_str = time_element.text.strip()
                    full_title = title_element.text.strip()
                    notification_id = f"{datetime.now().strftime('%Y-%m-%d')}_{time_str}"

                    if notification_id in sent_today:
                        continue

                    class_time = datetime.strptime(
                        f"{datetime.now().strftime('%Y-%m-%d')} {time_str}", "%Y-%m-%d %H:%M"
                    )
                    time_now = datetime.now()
                    minutes_until_class = (class_time - time_now).total_seconds() / 60

                    if 10 <= minutes_until_class < 16:
                        print(f"Sending notification for '{full_title}'")
                        message = (
                            f"🔔 *Class Reminder!* \n\nYour class **{full_title}** "
                            f"is starting in about 15 minutes."
                        )
                        send_telegram_notification(message)

                        sent_today.append(notification_id)
                        save_sent_notifications(sent_today)

    except Exception as e:
        print(f"An error occurred: {e}")
        send_telegram_notification(
            f"⚠️ **Scraper Error:**\nCould not fetch your daily schedule. Reason: {e}"
        )


if __name__ == "__main__":
    scrape_and_check_reminders()
