import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json

# --- CONFIGURATION (Load from Environment Variables) ---
LPU_USERNAME = os.getenv("LPU_USERNAME")
LPU_PASSWORD = os.getenv("LPU_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- STATE FILE ---
# This file will remember which notifications have been sent
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"

# --- URLS (You must find these by inspecting the MyClass website) ---
LOGIN_URL = "https://myclass.lpu.in"
SCHEDULE_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/tla/m.jsp"

def load_sent_notifications():
    """Loads the list of notifications that have already been sent today."""
    if not os.path.exists(SENT_NOTIFICATIONS_FILE):
        return []
    with open(SENT_NOTIFICATIONS_FILE, 'r') as f:
        data = json.load(f)
        # If the file is from a previous day, clear it
        if data.get("date") != datetime.now().strftime('%Y-%m-%d'):
            return []
        return data.get("sent_list", [])

def save_sent_notifications(sent_list):
    """Saves the list of sent notifications for today."""
    data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "sent_list": sent_list
    }
    with open(SENT_NOTIFICATIONS_FILE, 'w') as f:
        json.dump(data, f)

def send_telegram_notification(message: str):
    """Sends a message to your Telegram via the bot."""
    # ... (This function remains the same as before) ...

def scrape_and_check_reminders():
    """Scrapes the schedule and sends notifications for classes starting soon."""
    if not all([LPU_USERNAME, LPU_PASSWORD, BOT_TOKEN, CHAT_ID]):
        print("FATAL ERROR: Environment variables are missing.")
        return

    try:
        sent_today = load_sent_notifications()
        
        with requests.Session() as session:
            # 1. Log In (Same as before)
            session.post(LOGIN_URL, data={'user': LPU_USERNAME, 'pass': LPU_PASSWORD})
            
            # 2. Fetch schedule page
            response = session.get(SCHEDULE_URL)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 3. Parse events
            event_contents = soup.find_all('div', class_='fc-content')
            if not event_contents:
                print("No class events found on page.")
                return

            for content in event_contents:
                time_element = content.find('div', class_='fc-time')
                title_element = content.find('div', class_='fc-title')

                if time_element and title_element:
                    time_str = time_element.text.strip() # e.g., "11:00"
                    full_title = title_element.text.strip()
                    
                    # Create a unique ID for this class today
                    notification_id = f"{datetime.now().strftime('%Y-%m-%d')}_{time_str}"
                    
                    # Skip if we've already sent a notification for this class today
                    if notification_id in sent_today:
                        continue
                        
                    # --- The Core Logic ---
                    # Convert class time string to a datetime object for today
                    class_time = datetime.strptime(f"{datetime.now().strftime('%Y-%m-%d')} {time_str}", "%Y-%m-%d %H:%M")
                    time_now = datetime.now()
                    
                    minutes_until_class = (class_time - time_now).total_seconds() / 60
                    
                    # Check if the class is between 10 and 15 minutes away
                    if 10 <= minutes_until_class < 16:
                        print(f"Sending notification for {full_title} at {time_str}")
                        message = f"🔔 *Class Reminder!* \n\nYour class **{full_title}** is starting in about 15 minutes."
                        send_telegram_notification(message)
                        
                        # Add to the sent list and save
                        sent_today.append(notification_id)
                        save_sent_notifications(sent_today)

    except Exception as e:
        print(f"An error occurred: {e}")
        # To avoid spamming on errors, only send an error notification once per hour
        # (This is an advanced concept, for now we will just print it)

if __name__ == "__main__":
    scrape_and_check_reminders()