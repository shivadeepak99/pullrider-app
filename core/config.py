# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Secrets for the bot's own operation
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
BOT_NAME = os.getenv("GITHUB_APP_NAME", "pullrider")

# This is now only a fallback for your local testing, not used by end-users.
GEMINI_API_KEY_FALLBACK = os.getenv("GEMINI_API_KEY")

if not GITHUB_TOKEN or not GITHUB_WEBHOOK_SECRET:
    raise EnvironmentError(
        "GITHUB_TOKEN and GITHUB_WEBHOOK_SECRET must be set in .env file."
    )
