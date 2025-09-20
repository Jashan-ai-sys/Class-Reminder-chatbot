# common/reminders.py
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from common import db_helpers 
from .scraper import fetch_lpu_classes

sent_reminders = set()  # avoid duplicate reminders

def format_class_info(cls, start_time):
    """Helper: Format class details for debug/logging."""
    title = cls.get("title", "N/A").split(" by :")[0].strip()
    return f"{title} @ {start_time.strftime('%H:%M %p')}"

async def check_classes_and_send_reminders(application):
    """Recurring job: runs every 60s to check and send reminders."""
    IST = ZoneInfo("Asia/Kolkata")
    now = datetime.now(IST)
    print(f"[{now.strftime('%H:%M:%S')}] 🔎 Checking classes for reminders...")
    users_col = db_helpers.users_col
    if users_col is None:
        print("⚠️ users_col is None (DB not ready yet). Skipping this cycle.")
        return

    async for user in users_col.find({}):
        chat_id = user.get("chat_id")
        if not chat_id:
            continue

        try:
            reminder_minutes = await db_helpers.get_reminder_preference(chat_id)
            reminder_window = reminder_minutes * 60  # seconds
            data = await fetch_lpu_classes(chat_id)
            classes = data.get("classes") or data.get("ref") or data.get("data") or []

            for cls in classes:
                title = cls.get("title", "Class").strip()

                # --- Normalize startTime ---
                start_ms = cls.get("startTime")
                if not start_ms:
                    start_ms = cls.get("scheduledStartDayTime")
                    if start_ms:
                        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                        start_ms = int(today.timestamp() * 1000) + start_ms

                if not start_ms:
                    print(f"⚠️ Skipping {title}: no valid start time")
                    continue

                start_time = datetime.fromtimestamp(start_ms / 1000, tz=IST)
                time_to_class = (start_time - now).total_seconds()

                # Debug log for every class
                print(f"[DEBUG] {chat_id} → {title}: "
                      f"start={start_time.strftime('%H:%M')}, "
                      f"now={now.strftime('%H:%M')}, "
                      f"Δt={time_to_class:.0f}s, "
                      f"window={reminder_window}s")

                # Skip if not in reminder window
                if not (0 < time_to_class <= reminder_window):
                    continue

                # Avoid duplicate reminders
                class_id = cls.get("_id") or f"{title}_{start_ms}"
                reminder_key = f"{chat_id}_{class_id}"
                if reminder_key in sent_reminders:
                    continue

                # Send reminder
                msg = (
                    f"⏰ Reminder: '{title}' starts in {reminder_minutes} mins!"
                    if reminder_minutes > 0
                    else f"🔔 Your class '{title}' is starting now!"
                )
                await application.bot.send_message(chat_id=chat_id, text=msg)
                print(f"✅ Sent reminder → {chat_id} :: {title}")

                sent_reminders.add(reminder_key)

        except Exception as e:
            print(f"❌ Error for {chat_id}: {e}")
