import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION (Load from Environment Variables) ---
# You must set these in your hosting service's "Variables" section
LPU_USERNAME = os.getenv("LPU_USERNAME")
LPU_PASSWORD = os.getenv("LPU_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") # Your personal Telegram Chat ID

# --- URLS (You must find these by inspecting the MyClass website) ---
LOGIN_URL = "https://myclass.lpu.in" # The URL the login form submits to
SCHEDULE_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/tla/m.jsp" # The URL of your calendar page

def send_telegram_notification(message: str):
    """Sends a message to your Telegram via the bot."""
    if not all([BOT_TOKEN, CHAT_ID]):
        print("ERROR: Bot Token or Chat ID is not set.")
        return
        
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        print("Notification sent successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification: {e}")

def scrape_and_notify():
    """Logs into MyClass, scrapes the schedule, and sends a notification."""
    
    # 1. Check if all required variables are set
    if not all([LPU_USERNAME, LPU_PASSWORD, BOT_TOKEN, CHAT_ID]):
        print("FATAL ERROR: One or more environment variables are missing.")
        # Optionally send an error message to yourself if setup is wrong
        # send_telegram_notification("Scraper Error: One or more environment variables are missing.")
        return

    try:
        with requests.Session() as session:
            # 2. Log In to MyClass
            print("Attempting to log in...")
            login_payload = {
                'user': LPU_USERNAME,
                'pass': LPU_PASSWORD,
            }
            response = session.post(LOGIN_URL, data=login_payload)
            
            if "Dashboard" not in response.text: # Example check for successful login
                raise Exception("Login to MyClass failed. Please check credentials.")
            print("Login successful.")

            # 3. Fetch the schedule page
            print("Fetching schedule page...")
            response = session.get(SCHEDULE_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 4. Parse the HTML using the class names from your screenshot
            event_contents = soup.find_all('div', class_='fc-content')
            
            if not event_contents:
                message = "No classes found on the schedule page for today."
            else:
                classes = []
                for content in event_contents:
                    time_element = content.find('div', class_='fc-time')
                    title_element = content.find('div', class_='fc-title')

                    if time_element and title_element:
                        time = time_element.text.strip()
                        full_title = title_element.text.strip()
                        classes.append(f"- *{time}:* {full_title}")
                
                if not classes:
                    message = "No classes scheduled for today!"
                else:
                    today_str = datetime.now().strftime('%A, %d %B %Y')
                    message = f"📅 *Your Schedule for {today_str}*\n\n" + "\n".join(sorted(classes))
            
            # 5. Send the final notification
            send_telegram_notification(message)

    except Exception as e:
        print(f"An error occurred during the scraping process: {e}")
        send_telegram_notification(f"⚠️ **Bot Error:**\nCould not fetch your daily schedule. Reason: {e}")

if __name__ == "__main__":
    scrape_and_notify()