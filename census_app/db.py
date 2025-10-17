import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# --------------------------------------------------------
# Load Environment Variables (Render cloud deployment)
# --------------------------------------------------------

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Optional: DATABASE_URL fallback if provided directly by Render
DATABASE_URL = os.getenv("DATABASE_URL")

# --------------------------------------------------------
# Database Connection String
# --------------------------------------------------------
if DATABASE_URL:
    # Prefer DATABASE_URL (single string form) if it exists
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    # Otherwise build it manually from component variables
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        raise ValueError("❌ Database environment variables are not properly set.")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
    )

# --------------------------------------------------------
# SQLAlchemy Engine & Session
# --------------------------------------------------------
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# --------------------------------------------------------
# Optional: Test Connection
# --------------------------------------------------------
def test_connection():
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).fetchone()
            print(f"✅ [DB] Connected successfully → {version[0]}")
    except Exception as e:
        print(f"❌ [DB] Connection failed: {e}")

# --------------------------------------------------------
# Constants
# --------------------------------------------------------
USERS_TABLE = "users"
HOLDERS_TABLE = "holders"
HOUSEHOLD_MEMBERS_TABLE = "household_members"
HOLDING_LABOUR_TABLE = "holding_labour"
HOLDING_LABOUR_PERM_TABLE = "holding_labour_permanent"
HOLDER_SURVEY_PROGRESS_TABLE = "holder_survey_progress"

ROLE_HOLDER = "Holder"
ROLE_AGENT = "Agent"
ROLE_ADMIN = "Admin"

STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_APPROVED = "approved"

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

if __name__ == "__main__":
    test_connection()
