import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION (Load from Environment Variables) ---
LPU_USERNAME = os.getenv("LPU_USERNAME")
LPU_PASSWORD = os.getenv("LPU_PASSWORD")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- URLS (You will need to find these by inspecting the MyClass website) ---
LOGIN_URL = "https://myclass.lpu.in" # Example URL
SCHEDULE_URL = "https://lovelyprofessionaluniversity.codetantra.com/secure/tla/m.jsp" # Example URL for the calendar view

def send_telegram_notification(message: str):
    """Sends a message to your Telegram via the bot."""
    # ... (This function remains the same as before) ...

def scrape_schedule():
    """Logs into MyClass, scrapes the schedule from the calendar view, and returns it."""
    with requests.Session() as session:
        # 1. Log In (This part remains the same)
        print("Attempting to log in...")
        login_payload = {'user': LPU_USERNAME, 'pass': LPU_PASSWORD}
        response = session.post(LOGIN_URL, data=login_payload)
        if "Dashboard" not in response.text: # Example login check
            return "Could not log in to MyClass."
        print("Login successful.")

        # 2. Fetch the schedule page
        print("Fetching schedule page...")
        response = session.get(SCHEDULE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Parse the HTML using the correct class names from your screenshot
        
        # Find all the main content blocks for each event
        event_contents = soup.find_all('div', class_='fc-content') # <-- CORRECTED
        
        if not event_contents:
            return "Could not find any scheduled classes on the page."
            
        classes = []
        for content in event_contents:
            # Find the time and title elements within each event
            time_element = content.find('div', class_='fc-time') # <-- CORRECTED
            title_element = content.find('div', class_='fc-title') # <-- CORRECTED

            if time_element and title_element:
                time = time_element.text.strip()
                full_title = title_element.text.strip()
                
                # --- Parse the title string to get the details ---
                try:
                    # Example: "PETS13-Lecture by : 66768:Alok Kumar (..."
                    parts = full_title.split(' by : ')
                    course_code = parts[0].replace('-Lecture', '').strip()
                    faculty_part = parts[1].split(':')[1].split('(')[0].strip()
                    faculty = faculty_part
                    
                    classes.append(f"- *{time}:* {course_code} ({faculty})")
                except IndexError:
                    # If the title format is different, just add the raw title
                    classes.append(f"- *{time}:* {full_title}")
        
        if not classes:
            return "No classes scheduled for today!"
            
        # 4. Format the final message
        today_str = datetime.now().strftime('%A, %d %B %Y')
        message = f"📅 *Your Schedule for {today_str}*\n\n" + "\n".join(sorted(classes))
        return message

if __name__ == "__main__":
    schedule_message = scrape_schedule()
    send_telegram_notification(schedule_message)