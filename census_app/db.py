import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load .env from root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", 5432)
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# PostgreSQL connection URL
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Engine
try:
    engine = create_engine(DATABASE_URL, echo=False, future=True)
except Exception as e:
    print(f"Error connecting to database: {e}")
    engine = None
