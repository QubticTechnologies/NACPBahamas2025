import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env file")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Optional: Create a session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Utility function to get a session
def get_db_session():
    """
    Yields a new SQLAlchemy session
    Use with: `with get_db_session() as session:`
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
