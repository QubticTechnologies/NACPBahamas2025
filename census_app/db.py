from sqlalchemy import create_engine
import os

# Detect local or cloud
LOCAL_DEV = os.getenv("LOCAL_DEV", "False").lower() == "true"

if LOCAL_DEV:
    # Local dev settings
    DB_USER = os.getenv("DB_USER", "servey_census_user")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "servey_census")
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Use Render external DB URL
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://servey_census_user:pA16sWRzYkKqhOLJoLiiHcHnaRu7q3oJ@dpg-d3msd5s9c44c73ccd240-a.oregon-postgres.render.com/servey_census"
    )

# Check
if not DATABASE_URL or "None" in DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set or invalid!")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
