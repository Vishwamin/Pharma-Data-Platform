from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from config.config import Config
from src.logger import get_logger

logger = get_logger("DatabaseManager")

Base = declarative_base()

def get_db_engine():
    """
    Creates and tests SQLAlchemy database engine.
    Attempts PostgreSQL connection first. If local PostgreSQL server is offline,
    gracefully falls back to local SQLite database for uninterrupted local development.
    """
    # 1. Try PostgreSQL engine
    try:
        engine = create_engine(Config.POSTGRES_URI, echo=False, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Successfully connected to PostgreSQL database: {Config.POSTGRES_DB} at {Config.POSTGRES_HOST}")
        return engine
    except Exception as pg_err:
        logger.warning(f"PostgreSQL connection failed ({str(pg_err).splitlines()[0]}). Falling back to local SQLite DB...")

    # 2. Fallback to SQLite
    try:
        sqlite_engine = create_engine(Config.SQLITE_URI, echo=False)
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected to local SQLite database at: {Config.SQLITE_URI}")
        return sqlite_engine
    except Exception as sqlite_err:
        logger.error(f"Failed to connect to fallback database: {str(sqlite_err)}")
        raise sqlite_err

# Initialize engine instance
engine = get_db_engine()

# Create sessionmaker factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Yields a database session for transactions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
