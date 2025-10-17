import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Maintain compatibility
LOCAL_DEV = False  # kept only to avoid import errors

# Load environment variables (if present)
load_dotenv()

# Always use the Render Cloud Database
DB_USER = os.getenv("DB_USER", "servey_census_user")
DB_PASS = os.getenv("DB_PASS", "pA16sWRzYkKqhOLJoLiiHcHnaRu7q3oJ")
DB_HOST = os.getenv("DB_HOST", "dpg-d3msd5s9c44c73ccd240-a.oregon-postgres.render.com")
DB_NAME = os.getenv("DB_NAME", "servey_census")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

print(f"🔗 Connecting to {DB_HOST} (LOCAL_DEV={LOCAL_DEV})")

# SQLAlchemy Engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
