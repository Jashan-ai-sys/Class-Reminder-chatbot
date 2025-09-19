# common/reminders.py
import time
from datetime import datetime, timezone, timedelta
from telegram.ext import Application
from .db_helpers import users_col, get_reminder_preference
from .scraper import fetch_lpu_classes

# In-memory set to track reminders sent since the last restart
sent_reminders = set()

def format_reminder_message(cls: dict) -> str:
    """Formats a class dictionary into a user-friendly reminder message."""
    title = cls.get('title', 'N/A').split(' by :')[0].strip()
    
    start_time_ms = cls.get('startTime')
    if not start_time_ms:
        try:
            start_time_ms = cls['extra']['recurrence']['slots'][0]['start']
        except (KeyError, IndexError):
            return ""

    dt_utc = datetime.fromtimestamp(start_time_ms / 1000, tz=timezone.utc)
    dt_ist = dt_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
    formatted_time = dt_ist.strftime('%I:%M %p')

    return f"🔔 *Class Reminder!*\n\n`{title}` is starting soon at `{formatted_time}`."

async def check_classes_and_send_reminders(application: Application):
    """The main job that the scheduler runs every minute."""
    print(f"[{datetime.now()}] Running scheduled reminder check...")
    if users_col is None:
        return

    async for user in users_col.find({}):
        chat_id = user.get("chat_id")
        if not chat_id:
            continue

        try:
            reminder_minutes = await get_reminder_preference(chat_id)
            data = await fetch_lpu_classes(chat_id)
            
            for cls in data.get("classes", []):
                class_id = cls.get("_id")
                start_time_ms = cls.get('startTime') or cls.get('extra', {}).get('recurrence', {}).get('slots', [{}])[0].get('start')

                if not class_id or not start_time_ms:
                    continue

                now_ts = time.time()
                class_start_ts = start_time_ms / 1000
                time_to_class_sec = class_start_ts - now_ts
                reminder_window_sec = reminder_minutes * 60
                
                if 0 < time_to_class_sec <= reminder_window_sec:
                    reminder_key = f"{chat_id}_{class_id}"
                    if reminder_key not in sent_reminders:
                        message = format_reminder_message(cls)
                        if message:
                            await application.bot.send_message(
                                chat_id=chat_id, text=message, parse_mode='Markdown'
                            )
                            print(f"✅ Sent reminder for class {class_id} to {chat_id}")
                            sent_reminders.add(reminder_key)
        except Exception as e:
            print(f"❌ Failed to process reminders for chat_id {chat_id}: {e}")