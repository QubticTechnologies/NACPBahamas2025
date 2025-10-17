import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()  # Load local .env for dev

# -------------------------------
# Local dev toggle
# -------------------------------
LOCAL_DEV = os.getenv("LOCAL_DEV", "True").strip().lower() == "true"

# -------------------------------
# Database configuration
# -------------------------------
if LOCAL_DEV:
    # Local Postgres
    DB_USER = os.getenv("DB_USER", "postgres").strip()
    DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1").strip()
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "agri_census").strip()
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Render internal DB
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL not set for Render environment")
    # enforce psycopg2 dialect
    if DATABASE_URL.startswith("postgresql://"):
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

# -------------------------------
# Table Constants
# -------------------------------
USERS_TABLE = "users"
HOLDERS_TABLE = "holders"
HOUSEHOLD_MEMBERS_TABLE = "household_members"
HOLDING_LABOUR_TABLE = "holding_labour"
HOLDING_LABOUR_PERM_TABLE = "holding_labour_permanent"
HOLDER_SURVEY_PROGRESS_TABLE = "holder_survey_progress"

# -------------------------------
# Roles
# -------------------------------
ROLE_HOLDER = "Holder"
ROLE_AGENT = "Agent"
ROLE_ADMIN = "Admin"

# -------------------------------
# Status
# -------------------------------
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_APPROVED = "approved"

# -------------------------------
# Survey Config
# -------------------------------
TOTAL_SURVEY_SECTIONS = 5

# -------------------------------
# Email Settings
# -------------------------------
EMAIL_USER = os.getenv("EMAIL_USER", "your_email@example.com").strip()
EMAIL_PASS = os.getenv("EMAIL_PASS", "").strip()

# -------------------------------
# Enumerations & Constants
# -------------------------------
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

AG_TRAINING_OPTIONS = ["Yes", "No"]

PRIMARY_OCC_OPTIONS = ["Agriculture", "Other"]

OCCUPATION_OPTIONS = [
    "Agriculture", "Fishing", "Professional/ Technical", "Administrative/ Manager",
    "Sales", "Customer Service", "Tourism", "Not Economically Active", "Other"
]

RELATIONSHIP_OPTIONS = [
    "Spouse/ Partner", "Son", "Daughter", "In-Laws", "Grandchild",
    "Parent/ Parent-in-law", "Other Relative", "Non-Relative"
]

WORKING_TIME_OPTIONS = ["N", "F", "P", "P3", "P6", "P7"]
