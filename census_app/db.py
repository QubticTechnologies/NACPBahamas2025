import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL for Render (must include SSL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://servey_census_user:pA16sWRzYkKqhOLJoLiiHcHnaRu7q3oJ"
    "@dpg-d3msd5s9c44c73ccd240-a.oregon-postgres.render.com/servey_census?sslmode=require"
)

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set. Check your .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
