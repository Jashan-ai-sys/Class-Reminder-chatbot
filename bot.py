import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
import logging
import json
import os
import re
import io
from common.db_helpers import set_reminder_preference
import pickle
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
   # or whatever function you defined
from typing import Dict, List, Optional
import base64
from common.scraper import fetch_lpu_classes
from common.db_helpers import init_db
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from common.crypto import encrypt_password
from common.db_helpers import save_user,get_user
from datetime import datetime, timezone, timedelta
from telegram.ext import JobQueue
from common.db_helpers import get_reminder_preference
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# ============== TELEGRAM IMPORTS ==============
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

# ============== GOOGLE API IMPORTS ==============
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============== OTHER THIRD-PARTY IMPORTS ==============
import pytz
from ics import Calendar, Event
import pdfplumber
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, File, ReplyKeyboardMarkup, KeyboardButton

# ============== OPTIONAL COMPATIBILITY IMPORTS ==============
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Changed to INFO for better debugging
)
logger = logging.getLogger(__name__)


BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN loaded:", BOT_TOKEN[:10] if BOT_TOKEN else "None")
PORT = int(os.getenv("PORT", 8080))
APP_URL = os.getenv("APP_URL")
print(f"--- DEBUG: Attempting to set webhook to: {APP_URL}") 
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ==================== CONFIGURATION ====================
# IMPORTANT: Replace with your actual bot token from BotFather
CLASSES_FILE = "lpu_classes.json"
TEMPLATES_FILE = "schedule_templates.json"
TOKEN_STORAGE_FILE = "google_tokens.pickle"

# LPU Course mappings for better display
COURSE_INFO = {
    "CSE322": {"name": "Formal Languages & Automation Theory", "faculty": "Priyanka Gotter", "room": "MyClass-1"},
    "PETS13": {"name": "Data Structure II", "faculty": "Alok Kumar", "room": "MyClass-1"},
    "PEA306": {"name": "Analytical Skills II", "faculty": "Abhishek Raj", "room": "MyClass-1"},
    "CSE343": {"name": "Training in Programming", "faculty": "TBD", "room": "Lab"},
    "FIN214": {"name": "Intro to Financial Markets", "faculty": "TBD", "room": "MyClass-1"},
    "INT234": {"name": "Predictive Analytics", "faculty": "TBD", "room": "MyClass-1"},
    "INT374": {"name": "Data Analytics with Power BI", "faculty": "TBD", "room": "MyClass-1"},
    "PEV301": {"name": "Verbal Ability", "faculty": "TBD", "room": "MyClass-1"}
}
IST = timezone(timedelta(hours=5, minutes=30))
class LPUClassBot:
      # keep it empty so the AttributeError is gone
      #
    def __init__(self):
        self.start_time = datetime.now()
    async def reminders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Shows reminder time options to the user."""
        keyboard = [
            [
                InlineKeyboardButton("⏰ 10 mins before", callback_data="set_reminder_10"),
                InlineKeyboardButton("⏰ 5 mins before", callback_data="set_reminder_5"),
            ],
            [
                InlineKeyboardButton("🔔 At class time (0 mins)", callback_data="set_reminder_0"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please choose your preferred class reminder time:",
            reply_markup=reply_markup
        )
 

    async def myschedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_user.id
        try:
            data = await fetch_lpu_classes(chat_id)
            print(f"[DEBUG] myschedule_command called for chat_id={chat_id}") 

            classes = data.get("classes") or data.get("ref") or data.get("data") or []
            if not classes:
                await update.message.reply_text("🎉 No upcoming classes found.")
                return

            response_lines = []
            for cls in classes:
                title = cls.get("title", "Unknown Class").strip()
                start_ts = cls.get("startTime")
                end_ts = cls.get("endTime")

                if not start_ts or not end_ts:
                    print(f"⚠️ Skipping class (missing times): {cls}")
                    continue

                # ✅ Convert timestamps to IST
                start = datetime.fromtimestamp(start_ts / 1000, tz=IST)
                end = datetime.fromtimestamp(end_ts / 1000, tz=IST)

                status = cls.get("status", "unknown")
                join = cls.get("joinUrl", "")

                response_lines.append(
                    f"📚 {title}\n"
                    f"🕘 {start.strftime('%A, %d %B %Y %I:%M %p')} – {end.strftime('%I:%M %p')}\n"
                    f"📌 Status: {status}\n"
                    + (f"🔗 {join}\n" if join else "")
                    + "—" * 40
                )

            # ✅ Prevent empty message error
            if response_lines:
                await update.message.reply_text("\n".join(response_lines))
            else:
                await update.message.reply_text("🎉 No valid upcoming classes found.")

        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching classes: {e}")



    def load_classes(self) -> Dict:
        """Load classes from JSON file with error handling"""
        try:
            if os.path.exists(CLASSES_FILE):
                with open(CLASSES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    return {}
            return {}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading classes: {e}")
            return {}
    
    def format_class(cls):
        title = cls.get("title", "Unknown Class").strip()
        start = datetime.fromtimestamp(cls["startTime"] / 1000)
        end = datetime.fromtimestamp(cls["endTime"] / 1000)
        join = cls.get("joinUrl", "")
        return f"📚 {title}\n🕘 {start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}\n🔗 {join if join else 'No link'}"
    # In bot.py, inside the LPUClassBot class

    async def schedule_reminders(self, application, chat_id: int):
        try:
            # 1. Get the user's preferred reminder time from the database
            reminder_minutes = await get_reminder_preference(chat_id)
            print(f"Scheduling reminders for {chat_id} with a {reminder_minutes}-minute lead time.")

            data = await fetch_lpu_classes(chat_id)
            classes = data.get("ref") or data.get("data") or data.get("classes", [])

            for cls in classes:
                title = cls.get("title", "Class").strip()
                IST = ZoneInfo("Asia/Kolkata")
                start_time = datetime.fromtimestamp(cls["startTime"] / 1000, tz=IST)

                # 2. Use the user's preference to calculate the reminder time
                reminder_time = start_time - timedelta(minutes=reminder_minutes)
                delay = (reminder_time - datetime.now(IST)).total_seconds()
                if delay > 0:
                    application.job_queue.run_once(
                        lambda ctx: ctx.bot.send_message(
                            chat_id,
                            f"⏰ Reminder: '{title}' starts in {reminder_minutes} mins!"
                            if reminder_minutes > 0 else f"🔔 Your class '{title}' is starting now!"
                        ),
                        when=delay,
                        chat_id=chat_id,
                        )

            print(f"✅ Reminders scheduled for {chat_id}")
        except Exception as e:
            print(f"⚠️ Could not schedule reminders: {e}")


    def save_classes(self):
            """Save classes to JSON file with backup"""
            try:
                backup_file = f"{CLASSES_FILE}.backup"
                if os.path.exists(CLASSES_FILE):
                    os.rename(CLASSES_FILE, backup_file)
                
                with open(CLASSES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.classes, f, indent=2, ensure_ascii=False)
                
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                    
            except Exception as e:
                logger.error(f"Error saving classes: {e}")
                backup_file = f"{CLASSES_FILE}.backup"
                if os.path.exists(backup_file) and not os.path.exists(CLASSES_FILE):
                    try:
                        os.rename(backup_file, CLASSES_FILE)
                    except Exception as restore_error:
                        logger.error(f"Error restoring backup: {restore_error}")

    def parse_class_input(self, input_text: str) -> Optional[Dict]:
        """Parse class input with improved validation"""
        parts = [part.strip() for part in input_text.split('|')]
        
        if len(parts) < 2:
            return None
        
        try:
            class_name = parts[0].strip()
            class_time_str = parts[1].strip()
            reminder_minutes = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 15
            class_url = parts[3].strip() if len(parts) > 3 else ""
            notes = parts[4].strip() if len(parts) > 4 else ""
            
            time_formats = [
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d-%m-%Y %H:%M"
            ]
            
            class_time = None
            for fmt in time_formats:
                try:
                    class_time = datetime.strptime(class_time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not class_time:
                return None
            
            if reminder_minutes < 1 or reminder_minutes > 120:
                reminder_minutes = 15
            
            return {
                "name": class_name,
                "time": class_time.isoformat(),
                "reminder_minutes": reminder_minutes,
                "url": class_url,
                "notes": notes
            }
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None

    def add_class(self, user_id: int, class_data: Dict) -> int:
        """Add a new class with validation"""
        user_key = str(user_id)
        if user_key not in self.classes:
            self.classes[user_key] = []
        
        existing_ids = [cls.get('id', 0) for cls in self.classes[user_key]]
        new_id = max(existing_ids, default=0) + 1
        
        class_entry = {
            "id": new_id,
            "name": class_data["name"],
            "time": class_data["time"],
            "reminder_minutes": class_data["reminder_minutes"],
            "url": class_data["url"],
            "notes": class_data["notes"],
            "reminded": False,
            "created_at": datetime.now().isoformat()
        }
        
        self.classes[user_key].append(class_entry)
        self.save_classes()
        return new_id

    

    def get_user_classes(self, user_id: int):
        try:
            data = fetch_lpu_classes(user_id)
            return data.get("ref", []) or data.get("data", [])
        except Exception as e:
            print(f"❌ Error fetching classes for {user_id}: {e}")
            return []


    def remove_class(self, user_id: int, class_id: int) -> bool:
        """Remove a class by ID"""
        user_key = str(user_id)
        user_classes = self.classes.get(user_key, [])
        original_count = len(user_classes)
        self.classes[user_key] = [cls for cls in user_classes if cls.get("id") != class_id]
        
        if len(self.classes[user_key]) < original_count:
            self.save_classes()
            return True
        return False

    def clear_all_classes(self, user_id: int):
        """Remove all classes for a user."""
        user_key = str(user_id)
        if user_key in self.classes:
            self.classes[user_key] = []
            self.save_classes()

    def get_upcoming_classes(self, user_id: int, limit=1):
        classes = self.get_user_classes(user_id)
        if not classes:
            return []
        classes_sorted = sorted(classes, key=lambda x: x["startTime"])
        return classes_sorted[:limit]


    def get_course_info(self, class_name: str) -> Dict:
        """Get course information based on class name"""
        for code, info in COURSE_INFO.items():
            if code in class_name.upper():
                return info
        return {"name": class_name, "faculty": "TBD", "room": "TBD"}
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles the /start command with a greeting and interactive inline buttons."""
        user = update.effective_user
        chat_id = user.id

        greeting = (
            f"👋 Hey {user.first_name}!\n\n"
            "Hey there! Jashanprit here.\n"
            "👋Welcome to the *LPU Class Reminder Bot* 🎓\n\n"
            "I can help you:\n"
            "• View your upcoming classes 🗓️\n"
            "• Get reminders before they start ⏰\n"
            "• Manage your timetable 📚\n\n"
            "👇 Tap a button below to get started!"
        )

        # ✅ Inline menu (each button calls your button_callback)
        keyboard = [
            [InlineKeyboardButton("📅 My Schedule", callback_data="list_classes"),
            InlineKeyboardButton("🔔 Reminders", callback_data="reminders_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            greeting,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

        # DB check
        db_user = await get_user(chat_id)
        if db_user:
            await update.message.reply_text(
                f"🚀 Welcome back, *{user.first_name}*! "
                "Your reminders are active and I’ll keep you updated. ✅",
                parse_mode="Markdown"
            )
            await self.schedule_reminders(context.application, chat_id)
        else:
            frontend_url = os.getenv("FRONTEND_URL", "https://your-frontend.vercel.app")
            login_url = f"{frontend_url}?chat_id={chat_id}"
            login_keyboard = [[InlineKeyboardButton("🎓 Login with LPU Credentials", url=login_url)]]

            await update.message.reply_text(
                "👉 To get started, please log in with your LPU credentials so I can fetch your schedule.",
                reply_markup=InlineKeyboardMarkup(login_keyboard)
            )



    def cleanup_old_classes(self, days_old: int = 7):
        """Remove classes older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for user_id, user_classes in self.classes.items():
            self.classes[user_id] = [
                cls for cls in user_classes
                if datetime.fromisoformat(cls["time"]) > cutoff_date
            ]
        
        self.save_classes()
        logger.info("Old classes cleaned up.")
    async def send_reminder(self, user_id: int, class_data: Dict, is_test: bool = False):
        """Send reminder message to user"""
        try:
            class_time = datetime.fromisoformat(class_data["time"])
            course_info = self.get_course_info(class_data["name"])
            
            time_until = class_time - datetime.now()
            minutes_until = max(0, int(time_until.total_seconds() // 60))
            
            header = "🔔 *Class Reminder!*" if not is_test else "✅ *Test Reminder*"

            reminder_msg = f"""
{header}

📚 **{class_data['name']}**
📖 {course_info['name']}
👨‍🏫 {course_info['faculty']}
📅 {class_time.strftime('%A, %B %d')}
⏰ Starts in {minutes_until} minutes ({class_time.strftime('%I:%M %p')})

{f"🔗 [Join Class]({class_data['url']})" if class_data.get('url') else ""}
{f"📝 {class_data['notes']}" if class_data.get('notes') else ""}

Get ready! 🚀📖
            """
            
            keyboard = []
            if class_data.get('url'):
                keyboard.append([InlineKeyboardButton("🔗 Join Now", url=class_data['url'])])
            keyboard.append([InlineKeyboardButton("⏰ Next Classes", callback_data="list_classes")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            if self.application:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=reminder_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Send reminder error for user {user_id}: {e}")

# Create global bot instance
bot = LPUClassBot()

# ==================== COMMAND HANDLERS ====================

# In bot.py
# Make sure to import your new helper function
from common.db_helpers import get_user, save_user # Assuming you have these



async def addtimetable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add complete LPU timetable based on the corrected schedule image"""
    
    if not context.args:
        timetable_msg = """
🗓️ *Add Complete LPU Timetable*
*Based on the corrected schedule image*

*Usage Options:*
• `/addtimetable week` - Add current week's schedule
• `/addtimetable next` - Add next week's schedule  
• `/addtimetable custom YYYY-MM-DD` - Add from specific date

*📚 Your LPU Schedule Pattern (Mon-Fri):*

**Mon, Tue, Wed:**
• 09:00 AM & 10:00 AM - CSE322
• 11:00 AM - PETS13
• 01:00 PM & 02:00 PM - PEA306

**Thu, Fri:**
• 09:00 AM & 10:00 AM - CSE322
• 01:00 PM & 02:00 PM - PEA306
• 04:00 PM - PETS13

**Total Classes:** 25 per week (5 each day)
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📅 This Week", callback_data="timetable_week"),
                InlineKeyboardButton("📅 Next Week", callback_data="timetable_next")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            timetable_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Parse arguments
    option = context.args[0].lower()
    now = datetime.now()
    
    if option == "week":
        start_date = now - timedelta(days=now.weekday())
    elif option == "next":
        start_date = now - timedelta(days=now.weekday()) + timedelta(weeks=1)
    elif option == "custom" and len(context.args) > 1:
        try:
            start_date = datetime.strptime(context.args[1], '%Y-%m-%d')
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format! Use: YYYY-MM-DD\n"
                "Example: `/addtimetable custom 2025-09-15`"
            )
            return
    else:
        await update.message.reply_text(
            "❌ Invalid option!\n"
            "Use: `/addtimetable week`, `/addtimetable next`, or `/addtimetable custom YYYY-MM-DD`"
        )
        return
    
    # Your exact LPU timetable pattern based on the image
    added_count = 0
    failed_count = 0
    
    # Add classes for 5 days (Monday to Friday)
    for day_offset in range(5):
        class_date = start_date + timedelta(days=day_offset)
        day_name = class_date.strftime('%A')
        
        # Common classes for all weekdays
        daily_classes = [
            ("CSE322 FLAT", 9, 0, 15, "https://myclass.lpu.in/cse322", f"Formal Languages - Priyanka Gotter - {day_name}"),
            ("CSE322 FLAT", 10, 0, 10, "https://myclass.lpu.in/cse322", f"FLAT Class 2 - Priyanka Gotter - {day_name}"),
            ("PEA306 Analytics", 13, 0, 15, "https://myclass.lpu.in/pea306", f"Analytical Skills-II - Abhishek Raj - {day_name}"),
            ("PEA306 Analytics", 14, 0, 10, "https://myclass.lpu.in/pea306", f"Analytics Class 2 - Abhishek Raj - {day_name}")
        ]
        
        # Add the 5th class based on the day of the week
        if day_name in ['Monday', 'Tuesday', 'Wednesday']:
            # Mon/Tue/Wed: PETS13 is at 11 AM
            daily_classes.append(
                ("PETS13 DS-II", 11, 0, 15, "https://myclass.lpu.in/pets13", f"Data Structure-II - Alok Kumar - {day_name}")
            )
        elif day_name in ['Thursday', 'Friday']:
            # Thu/Fri: PETS13 is at 4 PM
            daily_classes.append(
                ("PETS13 DS-II", 16, 0, 15, "https://myclass.lpu.in/pets13", f"DS Evening - Alok Kumar - {day_name}")
            )
        
        # Add all classes for this day
        for class_name, hour, minute, reminder_min, url, notes in daily_classes:
            class_time = class_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            class_data = {
                "name": class_name,
                "time": class_time.isoformat(),
                "reminder_minutes": reminder_min,
                "url": url,
                "notes": notes
            }
            
            try:
                bot.add_class(update.effective_user.id, class_data)
                added_count += 1
            except Exception as e:
                logger.error(f"Failed to add class: {e}")
                failed_count += 1
    
    # Results message
    success_msg = f"""
✅ *LPU Timetable Added Successfully!*

📊 **Results:**
✅ Added: {added_count} classes
❌ Failed: {failed_count} classes

📅 **Schedule Period:**
From: {start_date.strftime('%A, %B %d, %Y')}
To: {(start_date + timedelta(days=4)).strftime('%A, %B %d, %Y')}

📚 **Your LPU Classes Added:**
• CSE322 FLAT - 10 sessions
• PETS13 DS-II - 5 sessions
• PEA306 Analytics - 10 sessions

⏰ **Schedule Pattern:**
• Mon-Fri: 5 classes each day

🔔 **Reminders:** All set up automatically
🌐 **MyClass Links:** Ready for quick joining

Use `/list` to view your complete schedule!
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📋 View Schedule", callback_data="list_classes"),
            InlineKeyboardButton("⏰ Next Class", callback_data="next_class")
        ],
        [
            InlineKeyboardButton("📊 Today's Classes", callback_data="today_classes"),
            InlineKeyboardButton("📅 This Week", callback_data="week_classes")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        success_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comprehensive help command"""
    help_text = """
🤖 *LPU Class Bot - Complete Guide*

*🗓️ Quick Timetable Setup:*
`/addtimetable week` - Add entire week's schedule (27 classes)
`/addtimetable next` - Add next week's schedule
`/addtimetable custom 2025-09-15` - From specific date

*📚 Manual Class Adding:*
`/add Class Name | YYYY-MM-DD HH:MM | Minutes | URL | Notes`

*🎯 Your LPU Course Examples:*
```

/add CSE322 FLAT | 2025-09-15 09:00 | 15 | [https://myclass.lpu.in/cse322](https://myclass.lpu.in/cse322) | Formal Languages - Priyanka Gotter

/add PETS13 DS-II | 2025-09-15 04:00 | 15 | [https://myclass.lpu.in/pets13](https://myclass.lpu.in/pets13) | Data Structure - Alok Kumar

/add PEA306 Analytics | 2025-09-15 13:00 | 20 | [https://myclass.lpu.in/pea306](https://myclass.lpu.in/pea306) | Analytical Skills - Abhishek Raj

```

*📋 Management Commands:*
• `/list` - Show all classes
• `/next` - Next upcoming class  
• `/today` - Today's schedule
• `/week` - This week's classes
• `/remove 1` - Delete class ID 1
• `/clear` - Remove all classes
• `/status` - Bot statistics
• `/test` - Test bot functionality

*💡 Pro Tips:*
• Bot sends automatic reminders
• Classes auto-save to file
• Use `/addtimetable week` for instant setup
• All classes include MyClass LPU links
• Respects your Project Work schedule

Need help? Just ask! 🎓
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def add_class_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced add class command"""
    if not context.args:
        example_text = """
📚 *Add Your LPU Class*

*Format:*
`/add Class Name | YYYY-MM-DD HH:MM | Minutes | URL | Notes`

*🎯 Your Course Examples:*
```

/add CSE322 FLAT | 2025-09-15 09:00 | 15 | [https://myclass.lpu.in/cse322](https://myclass.lpu.in/cse322) | Formal Languages - Priyanka Gotter

/add PETS13 DS-II | 2025-09-15 11:00 | 15 | [https://myclass.lpu.in/pets13](https://myclass.lpu.in/pets13) | Data Structure - Alok Kumar

/add PEA306 Analytics | 2025-09-15 13:00 | 20 | [https://myclass.lpu.in/pea306](https://myclass.lpu.in/pea306) | Analytical Skills - Abhishek Raj

```

*🗓️ Quick Option:*
Use `/addtimetable week` to add your complete weekly schedule automatically!
        """
        await update.message.reply_text(example_text, parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        input_text = ' '.join(context.args)
        parsed_data = bot.parse_class_input(input_text)
        
        if not parsed_data:
            await update.message.reply_text(
                "❌ *Invalid format!*\n\n"
                "Use: `/add Class Name | YYYY-MM-DD HH:MM | Minutes | URL | Notes`\n"
                "Example: `/add CSE322 FLAT | 2025-09-15 09:00 | 15 | https://myclass.lpu.in/cse322 | Formal Languages - Priyanka Gotter`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        class_id = bot.add_class(update.effective_user.id, parsed_data)
        course_info = bot.get_course_info(parsed_data["name"])
        class_time = datetime.fromisoformat(parsed_data["time"])
        
        success_msg = f"""
✅ *Class Added Successfully!*

📚 **{parsed_data['name']}**
📖 {course_info['name']}
👨‍🏫 {course_info['faculty']}
📅 {class_time.strftime('%A, %B %d')}
⏰ {class_time.strftime('%I:%M %p')}
🔔 {parsed_data['reminder_minutes']}-min reminder
🆔 ID: {class_id}
{f"🔗 [Join Class]({parsed_data['url']})" if parsed_data['url'] else ""}
{f"📝 {parsed_data['notes']}" if parsed_data['notes'] else ""}

I'll remind you when it's time! ⏰✨
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 View All Classes", callback_data="list_classes")],
            [InlineKeyboardButton("➕ Add Another", callback_data="help_add")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            success_msg, 
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error adding class: {e}")
        await update.message.reply_text(
            "❌ Something went wrong! Please check your format and try again.\n\n"
            "Use `/help` for examples! 📚"
        )

async def list_classes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced list command"""
    user_classes = bot.get_user_classes(update.effective_user.id)
    
    if not user_classes:
        await update.message.reply_text(
            "📚 *No classes scheduled yet!*\n\n"
            "Ready to add your LPU timetable?\n\n"
            "🚀 **Quick Setup:**\n"
            "`/addtimetable week` - Add complete weekly schedule\n\n"
            "📝 **Manual Add:**\n"
            "`/add CSE322 FLAT | 2025-09-15 09:00 | 15 | URL | Notes`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    now = datetime.now()
    upcoming_classes = [cls for cls in user_classes if datetime.fromisoformat(cls["time"]) > now]
    past_classes = [cls for cls in user_classes if datetime.fromisoformat(cls["time"]) <= now]
    
    message = f"📋 *Your LPU Classes ({len(user_classes)} total)*\n\n"
    
    if upcoming_classes:
        message += "⏰ *UPCOMING CLASSES:*\n"
        for cls in upcoming_classes[:10]: # Limit to 10 to avoid message overload
            try:
                class_time = datetime.fromisoformat(cls["time"])
                course_info = bot.get_course_info(cls["name"])
                time_diff = class_time - now
                
                if time_diff.days > 0:
                    time_until = f"in {time_diff.days} day(s)"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_until = f"in {hours}h"
                else:
                    minutes = time_diff.seconds // 60
                    time_until = f"in {minutes}min"
                
                message += f"""
🎯 **ID {cls['id']}** - {cls['name']}
📖 {course_info['name']}
👨‍🏫 {course_info['faculty']}
📅 {class_time.strftime('%a %b %d, %I:%M %p')}
⏱️ {time_until} • 🔔 {cls['reminder_minutes']}min
{f"🔗 [Link]({cls['url']})" if cls.get('url') else ""}
{f"📝 {cls['notes']}" if cls.get('notes') else ""}
━━━━━━━━━━━━━━━━
                """
            except (ValueError, KeyError):
                continue
    
    if past_classes:
        message += f"\n📜 *RECENT PAST CLASSES ({len(past_classes)}):*\n"
        for cls in past_classes[-3:]:
            try:
                class_time = datetime.fromisoformat(cls["time"])
                message += f"✅ **{cls['name']}** - {class_time.strftime('%a %b %d')}\n"
            except (ValueError, KeyError):
                continue
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ==================== NEWLY ADDED/COMPLETED FUNCTIONS ====================

async def next_class_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    try:
        data = fetch_lpu_classes(chat_id)
        classes = data.get("ref") or data.get("data") or []

        if not classes:
            await update.message.reply_text("🎉 No upcoming classes found.")
            return

        next_class = classes[0]
        title = next_class.get("title", "Unknown Class").strip()
        start = datetime.fromtimestamp(next_class["startTime"] / 1000)
        end = datetime.fromtimestamp(next_class["endTime"] / 1000)

        msg = (
            f"📚 *{title}*\n"
            f"🕘 {start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}\n"
        )
        if next_class.get("joinUrl"):
            msg += f"🔗 [Join Class]({next_class['joinUrl']})"

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching next class: {e}")


async def today_classes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    try:
        data = fetch_lpu_classes(chat_id)  # Fetch classes from scraper
        classes = data.get("ref") or data.get("data") or []

        if not classes:
            await update.message.reply_text("🎉 No classes today.")
            return

        msg_lines = []
        for cls in classes:
            title = cls.get("title", "Unknown Class").strip()
            start = datetime.fromtimestamp(cls["startTime"] / 1000)
            end = datetime.fromtimestamp(cls["endTime"] / 1000)

            msg_lines.append(
                f"📚 *{title}*\n🕘 {start.strftime('%I:%M %p')} – {end.strftime('%I:%M %p')}"
            )

        await update.message.reply_text("\n\n".join(msg_lines), parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching classes: {e}")



async def week_classes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows all classes for the current week."""
    user_classes = bot.get_user_classes(update.effective_user.id)
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    week_classes = [
        cls for cls in user_classes
        if start_of_week.date() <= datetime.fromisoformat(cls['time']).date() <= end_of_week.date()
    ]
    
    if not week_classes:
        await update.message.reply_text(
            "🗓️ No classes scheduled for this week. Use `/addtimetable week` to populate it.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
        
    message = f"🗓️ *This Week's Schedule ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')})*\n"
    
    classes_by_day = {}
    for cls in week_classes:
        day_name = datetime.fromisoformat(cls['time']).strftime('%A, %b %d')
        if day_name not in classes_by_day:
            classes_by_day[day_name] = []
        classes_by_day[day_name].append(cls)
        
    # Ensure days are sorted correctly
    sorted_days = sorted(classes_by_day.keys(), key=lambda d: datetime.strptime(d, '%A, %b %d'))

    for day in sorted_days:
        message += f"\n*--- {day.upper()} ---*\n"
        day_classes = sorted(classes_by_day[day], key=lambda x: x['time'])
        for cls in day_classes:
            class_time = datetime.fromisoformat(cls['time'])
            message += f"  • *{class_time.strftime('%I:%M %p')}* - {cls['name']}\n"
            
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def remove_class_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a class by its ID."""
    if not context.args:
        await update.message.reply_text("Please provide a class ID to remove. Usage: `/remove 123`")
        return
        
    try:
        class_id_to_remove = int(context.args[0])
        if bot.remove_class(update.effective_user.id, class_id_to_remove):
            await update.message.reply_text(f"✅ Successfully removed class with ID `{class_id_to_remove}`.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Could not find a class with ID `{class_id_to_remove}`. Use `/list` to see class IDs.", parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Please provide a number.")
    except Exception as e:
        logger.error(f"Error removing class: {e}")
        await update.message.reply_text("An error occurred while trying to remove the class.")

async def clear_classes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for confirmation to remove all classes."""
    keyboard = [
        [
            InlineKeyboardButton("⚠️ Yes, clear all my classes", callback_data="clear_confirm_yes"),
            InlineKeyboardButton("❌ No, keep them", callback_data="cancel_action")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "*⚠️ Are you sure you want to remove ALL your scheduled classes? This action cannot be undone.*",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows bot status and statistics."""
    uptime = datetime.now() - bot.start_time
    days, remainder = divmod(uptime.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    
    user_classes_count = len(bot.get_user_classes(update.effective_user.id))
    total_users_count = len(bot.classes)
    
    status_text = f"""
    🤖 *Bot Status & Stats*
    
    ✅ **Status:** Running
    
    ⏱️ **Uptime:** {int(days)}d {int(hours)}h {int(minutes)}m
    
    👤 **Your Classes:** {user_classes_count} scheduled
    
    👥 **Total Users:** {total_users_count}
    
    💾 **Data File:** `{CLASSES_FILE}` exists: {os.path.exists(CLASSES_FILE)}
    """
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a test reminder for the next upcoming class."""
    upcoming = bot.get_upcoming_classes(update.effective_user.id, limit=1)
    if not upcoming:
        await update.message.reply_text("No upcoming classes to send a test reminder for.")
        return
    
    await update.message.reply_text("Sending a test reminder for your next class...")
    await bot.send_reminder(update.effective_user.id, upcoming[0], is_test=True)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.from_user.id

    # --- Reminder preference buttons ---
    if data.startswith("set_reminder_"):
        minutes_str = data.split('_')[-1]
        minutes = int(minutes_str)

        # Save the preference to the database
        await set_reminder_preference(chat_id, minutes)

        feedback_text = (
            f"✅ Your reminders are now set to {minutes} minutes before each class."
            if minutes > 0 else
            "✅ Your reminders are now set for the exact start time of each class."
        )

        await query.edit_message_text(text=feedback_text)
        return

    # --- Menu buttons ---
    if data == "list_classes":
        await bot.myschedule_command(update, context)

    elif data == "next_class":
        await next_class_command(update, context)

    elif data == "today_classes":
        await today_classes_command(update, context)

    elif data == "week_classes":
        await week_classes_command(update, context)

    elif data == "help_add":
        context.args = []
        await add_class_command(update, context)

    elif data == "help_addtimetable":
        context.args = []
        await addtimetable_command(update, context)

    elif data == "show_help":
        await help_command(update, context)

    elif data == "timetable_week":
        await query.edit_message_text(
            text="Adding this week's timetable...",
            parse_mode=ParseMode.MARKDOWN
        )
        context.args = ["week"]
        await addtimetable_command(update, context)

    elif data == "timetable_next":
        await query.edit_message_text(
            text="Adding next week's timetable...",
            parse_mode=ParseMode.MARKDOWN
        )
        context.args = ["next"]
        await addtimetable_command(update, context)

    elif data == "clear_confirm_yes":
        bot.clear_all_classes(chat_id)
        await query.edit_message_text(
            text="✅ All your classes have been cleared.",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "cancel_action":
        await query.edit_message_text(text="Action cancelled.", parse_mode=ParseMode.MARKDOWN)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles main menu button presses from ReplyKeyboard."""
    text = update.message.text

    if text == "📅 My Schedule":
        await update.message.reply_text("📅 Fetching your schedule...")
        await bot.myschedule_command(update, context)

    elif text == "➡️ Next Class":
        await update.message.reply_text("➡️ Checking your next class...")
        await next_class_command(update, context)

    elif text == "📆 Today":
        await today_classes_command(update, context)

    elif text == "🗓️ This Week":
        await week_classes_command(update, context)

    elif text == "🔔 Reminders":
        await bot.reminders_command(update, context)

    elif text == "❓ Help":
        await help_command(update, context)

    elif text == "⚙️ Settings":
        await update.message.reply_text("⚙️ Settings will be available soon!")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 My Schedule", callback_data="myschedule")],
        [InlineKeyboardButton("📆 Today", callback_data="today_classes")],
        [InlineKeyboardButton("➡️ Next Class", callback_data="next_class")],
        [InlineKeyboardButton("🔔 Set Reminders", callback_data="reminders")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = (
        "ℹ️ *Help Menu*\n\n"
        "Here’s what I can do for you:\n"
        "• 📅 Show all your upcoming classes\n"
        "• 📆 View today’s classes\n"
        "• ➡️ Tell you the next class\n"
        "• 🔔 Configure class reminders\n\n"
        "Choose an option below 👇"
    )

    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=reply_markup)

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and sends an iCalendar (.ics) file of the user's schedule."""
    await update.message.reply_text("📅 Generating your schedule file, please wait...")

    user_classes = bot.get_user_classes(update.effective_user.id)
    
    if not user_classes:
        await update.message.reply_text("You have no classes scheduled to export.")
        return
        
    try:
        cal = Calendar()
        ist = pytz.timezone('Asia/Kolkata')

        for cls in user_classes:
            course_info = bot.get_course_info(cls["name"])
            
            # Create a timezone-aware datetime object for the class start time
            start_time_naive = datetime.fromisoformat(cls['time'])
            start_time_aware = ist.localize(start_time_naive)
            
            # Assume a class duration of 55 minutes
            end_time_aware = start_time_aware + timedelta(minutes=55)

            # Create the event description
            description = f"Course: {course_info['name']}\n"
            description += f"Faculty: {course_info['faculty']}\n"
            if cls.get('url'):
                description += f"Join Link: {cls['url']}"

            # Create and add the event
            event = Event()
            event.name = cls['name']
            event.begin = start_time_aware
            event.end = end_time_aware
            event.description = description
            event.location = course_info['room']
            cal.events.add(event)
            
        # Convert calendar to a string and then to bytes
        ics_data = str(cal).encode('utf-8')
        
        # Send the file as a document
        await update.message.reply_document(
            document=ics_data,
            filename="LPU_Schedule.ics",
            caption="Here is your schedule in .ics format. You can import this into Google Calendar, Outlook, or Apple Calendar."
        )

    except Exception as e:
        logger.error(f"Error generating .ics file: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while creating your schedule file.")
# ==================== GUIDED SCHEDULE SETUP ====================

# Define states for the conversation
SELECTING_DAY, AWAITING_TIME, AWAITING_CODE, CONFIRM_DAY_CONTINUE = range(4)

# --- Helper functions for loading/saving templates ---
def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_templates(templates):
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f, indent=2)

# --- Conversation step functions ---
async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the schedule setup conversation."""
    context.user_data['schedule_template'] = {} # Clear any previous template
    
    keyboard = [
        [InlineKeyboardButton("Mon", callback_data="Monday"), InlineKeyboardButton("Tue", callback_data="Tuesday")],
        [InlineKeyboardButton("Wed", callback_data="Wednesday"), InlineKeyboardButton("Thu", callback_data="Thursday")],
        [InlineKeyboardButton("Fri", callback_data="Friday")],
        [InlineKeyboardButton("✅ Save & Finish", callback_data="finish")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🗓️ Let's set up your repeating weekly schedule!\n\n"
        "Select a day to add classes for. When you're all done, press 'Save & Finish'.",
        reply_markup=reply_markup
    )
    return SELECTING_DAY

async def select_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user selecting a day or finishing."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "finish":
        return await setup_finish(update, context)

    selected_day = query.data
    context.user_data['current_day'] = selected_day
    
    await query.edit_message_text(
        f"Okay, adding classes for **{selected_day}**.\n\n"
        "Please send me the start time of your first class in 24-hour format (e.g., `09:00`, `16:00`).",
        parse_mode=ParseMode.MARKDOWN
    )
    return AWAITING_TIME

async def await_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user sending a class time."""
    time_text = update.message.text
    try:
        # Validate time format
        datetime.strptime(time_text, '%H:%M')
        context.user_data['current_time'] = time_text
        await update.message.reply_text(f"Got it, {time_text}. Now, what is the course code? (e.g., `CSE322`)", parse_mode=ParseMode.MARKDOWN)
        return AWAITING_CODE
    except ValueError:
        await update.message.reply_text("That doesn't look right. Please send the time in HH:MM format (e.g., `09:00`).")
        return AWAITING_TIME

async def await_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user sending a course code and saves the class."""
    course_code = update.message.text
    day = context.user_data['current_day']
    time = context.user_data['current_time']
    
    # Initialize day in template if not present
    if day not in context.user_data['schedule_template']:
        context.user_data['schedule_template'][day] = []
        
    # Add the class to the template
    context.user_data['schedule_template'][day].append({'time': time, 'code': course_code})
    
    keyboard = [
        [InlineKeyboardButton("Yes, add another", callback_data="yes")],
        [InlineKeyboardButton("No, pick another day", callback_data="no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👍 Added **{course_code}** at {time} on {day}s.\n\nAdd another class for {day}?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return CONFIRM_DAY_CONTINUE

async def confirm_day_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks user if they want to add another class to the current day."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "yes":
        day = context.user_data['current_day']
        await query.edit_message_text(f"Okay, what's the time for the next class on {day}?")
        return AWAITING_TIME
    else: # 'no'
        keyboard = [
            [InlineKeyboardButton("Mon", callback_data="Monday"), InlineKeyboardButton("Tue", callback_data="Tuesday")],
            [InlineKeyboardButton("Wed", callback_data="Wednesday"), InlineKeyboardButton("Thu", callback_data="Thursday")],
            [InlineKeyboardButton("Fri", callback_data="Friday")],
            [InlineKeyboardButton("✅ Save & Finish", callback_data="finish")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Which day would you like to configure next?",
            reply_markup=reply_markup
        )
        return SELECTING_DAY

async def setup_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the completed template and ends the conversation."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    templates = load_templates()
    templates[user_id] = context.user_data['schedule_template']
    save_templates(templates)
    
    await query.edit_message_text(
        "✅ All done! Your weekly schedule template has been saved.\n\n"
        "You can now use a command like `/generateschedule` to add these classes to your calendar for the week."
    )
    context.user_data.clear()
    return ConversationHandler.END

async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the setup process."""
    await update.message.reply_text("Schedule setup cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# Define the ConversationHandler
setup_handler = ConversationHandler(
    entry_points=[CommandHandler('setup', setup_start)],
    states={
        SELECTING_DAY: [CallbackQueryHandler(select_day)],
        AWAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, await_time)],
        AWAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, await_code)],
        CONFIRM_DAY_CONTINUE: [CallbackQueryHandler(confirm_day_continue)]
    },
    fallbacks=[CommandHandler('cancel', setup_cancel)],
    per_user=True,
    per_chat=True
)
from telegram import WebAppInfo # Add this to your telegram imports

# --- Functions for Web App ---
async def editschedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a button to launch the schedule editor web app with the user's ID."""
    user_id = update.effective_user.id
    # IMPORTANT: Replace this with your GitHub Pages URL
    base_url = "https://class-reminder-chatbot-53ay44pev-jashan-ai-sys-projects.vercel.app/"
    
    # We add the user's ID to the URL so the web app knows who is opening it
    url_with_user_id = f"{base_url}?user_id={user_id}"

    keyboard = [[
        InlineKeyboardButton(
            "Open Schedule Editor", 
            web_app=WebAppInfo(url=url_with_user_id)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Click the button below to open the visual editor. Your saved schedule will be loaded automatically.",
        reply_markup=reply_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles data received from the web app."""
    user_id = str(update.effective_user.id)
    data_str = update.message.web_app_data.data
    
    try:
        schedule_template = json.loads(data_str)
        
        templates = load_templates() # Assumes you have the load/save functions from the previous step
        templates[user_id] = schedule_template
        save_templates(templates)
        
        await update.message.reply_text(
            "✅ Your schedule has been saved successfully from the editor!\n\n"
            "You can now use `/generateschedule` to create the classes for the week."
        )
    except json.JSONDecodeError:
        await update.message.reply_text("Sorry, I received invalid data from the editor.")
    except Exception as e:
        logger.error(f"Error processing web app data: {e}")
        await update.message.reply_text("An error occurred while saving your schedule.")
async def generate_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates classes from the template, syncs to Google Calendar, and avoids duplicates."""
    user_id = str(update.effective_user.id)
    templates = load_templates()
    user_template = templates.get(user_id)

    if not user_template:
        await update.message.reply_text(
            "You haven't saved a schedule template yet. Please use the PDF upload or `/editschedule` to set one up first."
        )
        return

    await update.message.reply_text("Generating schedule and syncing with Google Calendar (checking for duplicates)...")
    
    # --- Google Calendar Integration ---
    google_creds = None
    tokens = load_google_tokens()
    if user_id in tokens:
        google_creds = tokens[user_id]
    
    if not google_creds or not google_creds.valid:
        if google_creds and google_creds.expired and google_creds.refresh_token:
            google_creds.refresh(Request())
        else:
            google_creds = None
    
    google_service = None
    if google_creds:
        try:
            google_service = build('calendar', 'v3', credentials=google_creds)
        except HttpError as error:
            logger.error(f"An error occurred building Google service: {error}")
            await update.message.reply_text("Could not connect to Google Calendar. Please try running /connect_calendar again.")
    
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    start_of_this_week = today - timedelta(days=today.weekday())
    day_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
    
    added_count = 0
    google_added_count = 0
    google_skipped_count = 0 # New counter for duplicates

    for day, classes in user_template.items():
        if day not in day_map: continue
        
        for class_info in classes:
            try:
                day_offset = day_map[day]
                class_date = start_of_this_week + timedelta(days=day_offset)
                if class_date.date() < today.date():
                    class_date += timedelta(weeks=7) # Schedule for next week

                hour, minute = map(int, class_info['time'].split(':'))
                start_time = class_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                end_time = start_time + timedelta(minutes=55)

                # 1. Add class to the bot's internal schedule
                class_data = {"name": class_info['code'], "time": start_time.isoformat(), "reminder_minutes": 15, "url": "", "notes": f"Class on {day}"}
                bot.add_class(update.effective_user.id, class_data)
                added_count += 1
                
                # 2. Add class to Google Calendar
                if google_service:
                    event_body = {
                        'summary': class_info['code'],
                        'location': 'MyClass LPU',
                        'description': f"Course: {class_info.get('notes', 'N/A')}",
                        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Kolkata'},
                        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Kolkata'},
                    }
                    
                    # --- NEW: Check for existing events before creating ---
                    events_result = google_service.events().list(
                        calendarId='primary',
                        timeMin=start_time.isoformat(),
                        timeMax=end_time.isoformat(),
                        q=class_info['code'], # Search for the event name
                        singleEvents=True
                    ).execute()
                    existing_events = events_result.get('items', [])

                    if not existing_events:
                        # If no event was found, create a new one
                        google_service.events().insert(calendarId='primary', body=event_body).execute()
                        google_added_count += 1
                    else:
                        # If an event already exists, skip it
                        google_skipped_count += 1
                    # --- END NEW ---

            except Exception as e:
                logger.error(f"Error generating class from template {class_info}: {e}")

    await update.message.reply_text(
        f"✅ **Sync Complete!**\n\n"
        f"Bot reminders generated: {added_count}\n"
        f"New events synced to Google Calendar: {google_added_count}\n"
        f"Duplicate events skipped: {google_skipped_count}"
    )
async def handle_pdf_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes an uploaded PDF timetable."""
    document = update.message.document
    if not document.file_name.lower().endswith('.pdf'):
        return # Should not happen if filter is correct, but good practice

    await update.message.reply_text("📄 Reading your PDF schedule, please wait...")
    
    try:
        pdf_file = await document.get_file()
        file_content_bytes = await pdf_file.download_as_bytearray()
        
        schedule_template = {}
        
        # Use io.BytesIO to treat the downloaded bytes as a file
        with pdfplumber.open(io.BytesIO(file_content_bytes)) as pdf:
            page = pdf.pages[0] # Assume the schedule is on the first page
            table = page.extract_table()
            
            if not table:
                await update.message.reply_text("❌ I couldn't find a table in that PDF. Please try another file.")
                return

            headers = [h.strip() for h in table[0]] # e.g., ['Timing', 'Monday', 'Tuesday', ...]
            
            # Loop through rows, skipping the header
            for row in table[1:]:
                time_str = row[0]
                if not time_str: continue
                
                # Extract the start time (e.g., '09' from '09-10 AM') and format it
                start_hour = time_str.split('-')[0].strip()
                if len(start_hour) == 1: start_hour = f"0{start_hour}"
                start_time = f"{start_hour}:00"

                # Loop through cells in the row, corresponding to days
                for i, cell_text in enumerate(row[1:]):
                    if not cell_text: continue
                    
                    # Use regex to find the course code (e.g., 'CSE322')
                    match = re.search(r'C:([A-Z0-9]+)', cell_text)
                    if match:
                        course_code = match.group(1)
                        day = headers[i + 1] # Get day from header using column index
                        
                        if day not in schedule_template:
                            schedule_template[day] = []
                        
                        schedule_template[day].append({'time': start_time, 'code': course_code})
        
        # Save the extracted template
        user_id = str(update.effective_user.id)
        templates = load_templates()
        templates[user_id] = schedule_template
        save_templates(templates)
        
        await update.message.reply_text(
            f"✅ Success! I've extracted and saved your weekly schedule from the PDF.\n\n"
            f"You can now use `/editschedule` to view or modify it, or use `/generateschedule` to create this week's classes."
        )

    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while processing your PDF file.")
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checks the file extension of a document and calls the correct handler."""
    doc = update.message.document
    if doc and doc.file_name:
        file_name = doc.file_name.lower()
        if file_name.endswith('.pdf'):
            await handle_pdf_schedule(update, context)
        elif file_name.endswith('.csv'):
            await handle_schedule_upload(update, context)
        else:
            await update.message.reply_text("I'm not sure what to do with this file type.")

# Define the scope: what permission we are asking for.
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_STORAGE_FILE = "google_tokens.pickle"

def load_google_tokens():
    """Loads all user tokens from the pickle file."""
    if os.path.exists(TOKEN_STORAGE_FILE):
        with open(TOKEN_STORAGE_FILE, 'rb') as token:
            return pickle.load(token)
    return {}

def save_google_tokens(tokens):
    """Saves all user tokens to the pickle file."""
    with open(TOKEN_STORAGE_FILE, 'wb') as token:
        pickle.dump(tokens, token)

async def connect_calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the Google Calendar authorization flow."""
    
    # Get the Base64 encoded string from the environment variable
    base64_secrets = os.getenv("GOOGLE_CLIENT_SECRET_JSON")
    if not base64_secrets:
        logger.error("GOOGLE_CLIENT_SECRET_JSON environment variable not set.")
        await update.message.reply_text("Server configuration error. Could not find Google credentials.")
        return

    # Decode the Base64 string back into a normal JSON string
    client_secrets_str = base64.b64decode(base64_secrets).decode('utf-8')
    client_config = json.loads(client_secrets_str)
    
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = 'http://localhost:8080/'
    
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true'
    )
    context.user_data['google_auth_state'] = state
    
    await update.message.reply_text(
        "Please authorize access to your Google Calendar:\n\n"
        "1. Click the link below to open the Google sign-in page.\n"
        "2. Sign in and click 'Allow'.\n"
        "3. You will be redirected to a page that says 'This site can’t be reached'. This is normal.\n"
        "4. **Copy the entire URL** from your browser's address bar and **paste it back here in the chat.**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Authorize with Google", url=authorization_url)]])
    )

async def handle_google_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the callback URL pasted by the user."""
    if 'google_auth_state' not in context.user_data:
        return

    url_text = update.message.text
    state = context.user_data.pop('google_auth_state')

    try:
        base64_secrets = os.getenv("GOOGLE_CLIENT_SECRET_JSON")
        client_secrets_str = base64.b64decode(base64_secrets).decode('utf-8')
        client_config = json.loads(client_secrets_str)

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES, state=state)
        flow.redirect_uri = 'http://localhost:8080/'
        
        flow.fetch_token(authorization_response=url_text)
        credentials = flow.credentials

        user_id = str(update.effective_user.id)
        tokens = load_google_tokens()
        tokens[user_id] = credentials
        save_google_tokens(tokens)
        
        await update.message.reply_text("✅ Success! Your Google Calendar has been connected.")
        
    except Exception as e:
        logger.error(f"Error handling Google callback: {e}")
        await update.message.reply_text("❌ An error occurred during authorization. Please try again by running /connect_calendar.")


def main():
    """Starts the bot and registers all handlers."""
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set. Please add your token to the script.")
        return None

    

    # Register all handlers on telegram_app
    telegram_app.add_handler(setup_handler)
    telegram_app.add_handler(CommandHandler("editschedule", editschedule_command))
    telegram_app.add_handler(CommandHandler("generateschedule", generate_schedule_command))
    telegram_app.add_handler(CommandHandler("connect_calendar", connect_calendar_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'localhost:8080'), handle_google_callback))
    telegram_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    telegram_app.add_handler(CommandHandler("start", bot.start_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("add", add_class_command))
    telegram_app.add_handler(CommandHandler("list", list_classes_command))
    telegram_app.add_handler(CommandHandler("remove", remove_class_command))
    telegram_app.add_handler(CommandHandler("addtimetable", addtimetable_command))
    telegram_app.add_handler(CommandHandler("next", next_class_command))
    telegram_app.add_handler(CommandHandler("reminders", bot.reminders_command))
    telegram_app.add_handler(CommandHandler("today", today_classes_command))
    telegram_app.add_handler(CommandHandler("week", week_classes_command))
    telegram_app.add_handler(CommandHandler("clear", clear_classes_command))
    telegram_app.add_handler(CommandHandler("status", status_command))
    telegram_app.add_handler(CommandHandler("test", test_command))
    telegram_app.add_handler(CommandHandler("export", export_command))
    telegram_app.add_handler(CommandHandler("myschedule", bot.myschedule_command))
    telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
    )

    async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print("[DEBUG UPDATE]", update)  # <- will print every update in Railway logs
        if update.message:
            await update.message.reply_text("✅ Bot received your message!")

    telegram_app.add_handler(MessageHandler(filters.ALL, debug_all))
    telegram_app.add_handler(CallbackQueryHandler(button_callback))
    print("✅ Handlers registered:", telegram_app.handlers)


    return telegram_app


if __name__ == "__main__":
    application = main()
    if application:
        application.run_polling()


    
    