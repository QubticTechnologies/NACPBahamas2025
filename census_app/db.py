import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()  # Loads local .env during dev

# -------------------------------
# Local dev toggle
# -------------------------------
LOCAL_DEV = os.getenv("LOCAL_DEV")
if LOCAL_DEV is None:
    raise ValueError("❌ LOCAL_DEV environment variable must be set")
LOCAL_DEV = LOCAL_DEV.lower() == "true"

# -------------------------------
# Database configuration
# -------------------------------
if LOCAL_DEV:
    # Local Postgres
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", 5432)
    DB_NAME = os.getenv("DB_NAME", "agri_census")
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Render internal DB
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL not set for Render environment")
    # Optional: enforce psycopg2 dialect
    if not DATABASE_URL.startswith("postgresql+psycopg2://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

# -------------------------------
# SQLAlchemy engine & session
# -------------------------------
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# -------------------------------
# Optional: test connection
# -------------------------------
def test_connection():
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).fetchone()
            print(f"✅ [DB] Connected successfully → {version[0]}")
    except Exception as e:
        print(f"❌ [DB] Connection failed: {e}")

# -------------------------------
# Run test
# -------------------------------
if __name__ == "__main__":
    test_connection()
