import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# --------------------------------------------------------
# Load environment variables
# --------------------------------------------------------
load_dotenv()

# --------------------------------------------------------
# Determine environment
# --------------------------------------------------------
LOCAL_DEV = os.getenv("LOCAL_DEV", "True").lower() in ("1", "true", "yes")

# --------------------------------------------------------
# Database configuration
# --------------------------------------------------------
if LOCAL_DEV:
    DB_USER = os.getenv("LOCAL_DB_USER", "agri_user")
    DB_PASSWORD = os.getenv("LOCAL_DB_PASSWORD", "sherline10152")
    DB_HOST = os.getenv("LOCAL_DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("LOCAL_DB_PORT", 5432)
    DB_NAME = os.getenv("LOCAL_DB_NAME", "agri_census")
    SSLMODE = "disable"  # local DB usually has no SSL
else:
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", 5432)
    DB_NAME = os.getenv("DB_NAME")
    SSLMODE = "require"  # cloud DB requires SSL

# --------------------------------------------------------
# Validate environment variables
# --------------------------------------------------------
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    raise ValueError("❌ Database environment variables are not properly set.")

# --------------------------------------------------------
# Create Database URL
# --------------------------------------------------------
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={SSLMODE}"

# --------------------------------------------------------
# SQLAlchemy Engine & Session
# --------------------------------------------------------
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# --------------------------------------------------------
# Optional test connection
# --------------------------------------------------------
def test_connection():
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT NOW();")).fetchone()
            print(f"✅ Database connected successfully → {version[0]}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

# --------------------------------------------------------
# Table Constants
# --------------------------------------------------------
USERS_TABLE = "users"
HOLDERS_TABLE = "holders"
HOUSEHOLD_MEMBERS_TABLE = "household_members"
HOLDING_LABOUR_TABLE = "holding_labour"
HOLDING_LABOUR_PERM_TABLE = "holding_labour_permanent"
HOLDER_SURVEY_PROGRESS_TABLE = "holder_survey_progress"

# --------------------------------------------------------
# Roles & Status
# --------------------------------------------------------
ROLE_HOLDER = "Holder"
ROLE_AGENT = "Agent"
ROLE_ADMIN = "Admin"

STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_APPROVED = "approved"

# --------------------------------------------------------
# Survey & Misc Options
# --------------------------------------------------------
TOTAL_SURVEY_SECTIONS = 5
SEX_OPTIONS = ["Male", "Female", "Other"]
MARITAL_STATUS_OPTIONS = [
    "Single", "Married", "Divorced", "Separated", "Widowed",
    "Common-Law", "Prefer not to disclose"
]
NATIONALITY_OPTIONS = ["Bahamian", "Other"]
EDUCATION_OPTIONS = [
    "No Schooling", "Primary", "Junior Secondary", "Senior Secondary",
    "Undergraduate", "Masters", "Doctorate", "Vocational", "Professional Designation"
]

# --------------------------------------------------------
# Run test connection if executed directly
# --------------------------------------------------------
if __name__ == "__main__":
    print(f"🔍 LOCAL_DEV = {LOCAL_DEV}")
    print(f"🔗 DATABASE_URL = {DATABASE_URL}")
    test_connection()
