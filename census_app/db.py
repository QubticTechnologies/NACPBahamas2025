import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

LOCAL_DEV = os.getenv("LOCAL_DEV", "False").lower() == "true"

if LOCAL_DEV:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_NAME = os.getenv("DB_NAME", "agri_census")
    engine = create_engine(
        f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    )
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    # Add SSL requirement for Render PostgreSQL
    if DATABASE_URL and "sslmode" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
    engine = create_engine(DATABASE_URL)
