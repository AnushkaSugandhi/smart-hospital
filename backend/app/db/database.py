import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger("smart_hospital.db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smart_hospital.db")

# Fix Heroku / Render legacy postgres:// prefix for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    # Test connection
    with engine.connect() as conn:
        logger.info(f"Database connected successfully with {DATABASE_URL.split('@')[-1]}")
except Exception as e:
    logger.warning(f"Could not connect to configured DATABASE_URL: {e}. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///./smart_hospital.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
