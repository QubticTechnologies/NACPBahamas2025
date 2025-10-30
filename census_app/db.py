# db.py
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Load database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create session
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base class for models
Base = declarative_base()





load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "agri_census")
DB_SSLMODE = os.getenv("DB_SSLMODE", "disable")

# Correct SQLAlchemy connection string
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?sslmode={DB_SSLMODE}"
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={},  # Ensures no SSL args are forced
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_connection():
    return engine.connect()

DB_PASS = os.getenv("DB_PASS", "sherline10152")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "agri_census")

DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Connecting to: {DATABASE_URI.replace(DB_PASS, '***')}")  # Mask password

engine = create_engine(DATABASE_URI)

# Test connection
try:
    with engine.connect() as conn:
        print("Database connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")

