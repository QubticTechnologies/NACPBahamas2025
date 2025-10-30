from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://servey_census_user:pA16sWRzYkKqhOLJoLiiHcHnaRu7q3oJ@dpg-d3msd5s9c44c73ccd240-a.oregon-postgres.render.com:5432/servey_census?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
