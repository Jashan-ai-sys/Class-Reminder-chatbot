LPU Class Schedule & Reminder Bot 🎓
A Telegram bot designed to help Lovely Professional University (LPU) students stay updated with their class schedules. It automatically fetches the timetable from MyClass, caches the session for efficiency, and can be configured to send timely reminders before each class.

Features
Automated Timetable Fetching: Securely logs into LPU MyClass using Playwright to scrape the class schedule.

Efficient Session Caching: Caches the login session cookie in the database to avoid slow browser logins on every request, making subsequent fetches nearly instantaneous.

Deployment Ready: Built with FastAPI to handle Telegram Webhooks, making it efficient and ready for production deployment on platforms like Railway.

Secure Credential Storage: Uses the cryptography library to encrypt and decrypt user passwords before storing them in MongoDB.

Robust Error Handling: Includes SSL verification fixes for aiohttp and Playwright to ensure stability in various server environments.

Tech Stack
Backend: Python, FastAPI

Telegram Bot: python-telegram-bot

Web Scraping: Playwright

Database: MongoDB (with motor for async access)

Security: cryptography for password encryption

Deployment: Railway, Gunicorn, Uvicorn

🤖 Bot Commands
Once the bot is running, you can interact with it in your Telegram chat using these commands:

/start

Displays a welcome message and initializes the bot for your chat.

/myschedule

Fetches and displays your class schedule for the current day. This is the main command to get your timetable.

🚀 Local Setup and Installation
Follow these steps to run the bot on your local machine for development and testing.

1. Prerequisites
Python 3.11+

Git

A MongoDB database (you can get a free one from MongoDB Atlas)

2. Clone the Repository
Bash

git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
3. Set Up a Virtual Environment
Bash

# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
4. Install Dependencies
Make sure you have a requirements.txt file with all the necessary libraries.

Plaintext

# requirements.txt
python-telegram-bot[webhooks]
fastapi
uvicorn
gunicorn
aiohttp
playwright
motor
cryptography
python-dotenv
certifi
Then, run the installation command:

Bash

pip install -r requirements.txt
5. Install Playwright Browsers
This command downloads the necessary browser binaries for Playwright.

Bash

playwright install --with-deps
6. Configure Environment Variables
Create a file named .env in the root of your project and add the following variables.

Code snippet

# Your Telegram Bot Token from BotFather
TELEGRAM_TOKEN="your_telegram_bot_token"

# Your MongoDB connection string
MONGO_URI="your_mongodb_connection_string"

# A secret key for encrypting passwords
# Generate one by running: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY="your_generated_secret_key"

# The public URL of your deployed app (for production)
# For local testing, this can be a placeholder
WEBHOOK_URL="https://your-app-name.up.railway.app"
🛠️ Running the Bot Locally
For local development, it's easiest to use Telegram's polling method. You can add a small block to the end of your main.py file to enable this.

Modify main.py for Polling (Optional but Recommended for Dev)
Add this if __name__ == "__main__": block to the end of your main.py. This part will only run when you execute the file directly, not when Gunicorn runs it in production.

Python

# Add this at the end of your main.py

if __name__ == "__main__":
    # This block is for local development using polling
    print("Starting bot in polling mode for local development...")

    # Initialize database
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("myschedule", schedule_command))

    # Start polling
    application.run_polling()
Run the Bot

Bash

python main.py
Your bot is now running locally and will respond to commands in your Telegram chat.

☁️ Deployment to Railway
Follow these steps to deploy your bot as a production-ready web service.

1. Create a Procfile
Create a file named Procfile (no extension) in your project root with this exact content:

web: gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
2. Push to GitHub
Commit all your files (main.py, Procfile, requirements.txt, the common folder) and push them to a GitHub repository.

3. Deploy on Railway
Create a New Project: Log in to your Railway dashboard and create a new project, selecting "Deploy from GitHub repo".

Select Your Repository: Choose the repository for your bot.

Configure Service Settings:

Go to your new service's "Settings" tab.

Under the "Build" section, set the Build Command to:

Bash

pip install -r requirements.txt && playwright install --with-deps
Add Environment Variables:

Go to the "Variables" tab.

Add all the secrets from your .env file: MONGO_URI, TELEGRAM_TOKEN, and ENCRYPTION_KEY.

Railway will provide a public URL for your service (e.g., my-bot.up.railway.app). Add this as the WEBHOOK_URL variable.

Check the Logs: Monitor the "Deployments" tab. The logs will show the build process and your bot starting up. The startup event in main.py will automatically set the webhook with Telegram.

Your bot is now live and will respond to commands instantly!