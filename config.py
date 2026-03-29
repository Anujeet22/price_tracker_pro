import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file and loads all variables

SECRET_KEY    = os.getenv("SECRET_KEY", "fallback-secret-key")

DB_CONFIG = {
    "host":     "localhost",
    "database": "pricetracker",
    "user":     "ptuser",
    "password": os.getenv("DB_PASSWORD"),
    "port":     "5432"
}

# Mail Settings
MAIL_SERVER='smtp.gmail.com'
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=os.getenv("MAIL_USERNAME")
MAIL_PASSWORD=os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER=os.getenv("MAIL_USERNAME")
