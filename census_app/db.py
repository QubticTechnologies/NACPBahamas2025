import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

LOCAL_DEV = os.getenv("LOCAL_DEV", "True").lower() == "true"

if LOCAL_DEV:

    DB_USER = os.getenv("DB_USER", "servey_census_user")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_NAME = os.getenv("DB_NAME", "servey_census")
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}")
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
