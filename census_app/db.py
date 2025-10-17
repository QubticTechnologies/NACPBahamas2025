import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# --------------------------------------------------------
# Load environment variables
# --------------------------------------------------------
load_dotenv()

# --------------------------------------------------------
# Render Cloud Database Connection (Always Use Cloud)
# --------------------------------------------------------
DB_USER = os.getenv("DB_USER", "servey_census_user")
DB_PASS = os.getenv("DB_PASS", "pA16sWRzYkKqhOLJoLiiHcHnaRu7q3oJ")
DB_HOST = os.getenv("DB_HOST", "dpg-d3msd5s9c44c73ccd240-a.oregon-postgres.render.com")
DB_NAME = os.getenv("DB_NAME", "servey_census")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# Create engine with pre-ping for stability
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

print(f"✅ Connected to Render Cloud DB: {DB_HOST}")
