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