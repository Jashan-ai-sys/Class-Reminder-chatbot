📅 LPU Class Reminder Bot

A comprehensive Telegram bot designed to help LPU students manage their class schedules, get timely reminders, and automate their weekly setup.

This bot has evolved from a simple reminder tool to a feature-rich assistant with multiple ways to import and manage your timetable.

✨ Features

Automatic Class Reminders → Get notified 10–15 minutes before every class.

Multiple Import Methods:

📄 PDF Parsing – Send your official LPU timetable PDF, and the bot reads it automatically.

🖥️ Visual Web Editor – A grid-based editor to manage your weekly schedule.

🤖 Guided Setup – Step-by-step conversational setup inside Telegram.

📊 CSV Upload – Import your schedule via a CSV file.

Calendar Export → Generate an .ics file for Google Calendar, Apple Calendar, or Outlook.

Schedule Management → View your daily/weekly schedule or check your next class quickly.

🚀 Commands and Usage
📌 Main Commands
Command	Description
/start	Displays welcome message and main commands.
/help	Shows a detailed guide on all features.
/list	Lists all currently scheduled classes.
/next	Shows details for your next upcoming class.
/today	Lists today’s classes.
/week	Displays the schedule for the current week.
/remove <ID>	Deletes a specific class (get ID from /list).
/clear	Removes all scheduled classes (with confirmation).
📌 Schedule Setup Commands
Command	Description
/editschedule	Opens the visual, web-based editor for weekly schedule.
/generateschedule	Creates upcoming week’s classes from template.
/setup	Starts a guided setup for your weekly schedule.
/importschedule	Instructions for importing via CSV.
/cancel	Cancels an ongoing process (like setup).
📌 Utility Commands
Command	Description
/export	Generates an .ics calendar file of your schedule.
/test	Sends a test notification.
/status	Shows bot statistics and uptime.
📌 Automatic Actions (No Command Needed)

Send a PDF → Bot reads timetable and saves it as your template.

Send a CSV → Bot processes the file and schedules classes.

🛠️ Installation and Setup
1️⃣ Prerequisites

Python 3.8+

A Telegram Bot Token from @BotFather

2️⃣ Basic Bot Setup
# Clone repository
git clone <your-repo-url>
cd <your-repo-name>

# Create requirements.txt with dependencies
echo "python-telegram-bot
ics
pytz
pdfplumber
Flask
Flask-Cors" > requirements.txt

# Install dependencies
pip install -r requirements.txt


Open lpu_bot.py and replace:

BOT_TOKEN = "YOUR_BOT_TOKEN"


Run the bot:

python lpu_bot.py

3️⃣ Advanced Setup (Visual Web Editor)

The /editschedule feature needs extra deployment:

🔹 Deploy API Server

Deploy server.py to a hosting service (e.g. Render, Heroku, PythonAnywhere).

Get the public URL (e.g. https://your-flask-server.onrender.com).

🔹 Deploy Frontend Web App

Host index.html, style.css, app.js on GitHub Pages / Netlify.

Get the public URL (e.g. https://your-username.github.io/your-repo-name/).

🔹 Connect Everything

In app.js, update:

const API_SERVER_URL = "https://your-flask-server.onrender.com";


In lpu_bot.py, update the URL in editschedule_command with your frontend URL.

Restart the bot and ensure both server + frontend are live.

📂 Project Structure
📦 lpu-class-reminder-bot
 ┣ 📜 lpu_bot.py           # Main Telegram bot
 ┣ 📜 server.py            # API server for visual editor
 ┣ 📜 requirements.txt     # Dependencies
 ┣ 📂 web_editor/          # Web frontend (index.html, style.css, app.js)
 ┗ 📜 README.md            # Documentation

📌 Roadmap

 Add Google Calendar API sync.

 Support for recurring semester templates.

 Add AI-powered PDF parsing for messy timetables.

🤝 Contributing

Pull requests are welcome! Please fork the repo and open a PR with improvements.

📜 License

MIT License. Feel free to use and modify.
