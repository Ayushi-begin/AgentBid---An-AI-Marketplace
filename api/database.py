import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from api.config import settings

logger = logging.getLogger(__name__)

# Fallback handling for database connection
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql") and "+psycopg2" not in db_url and "+asyncpg" not in db_url:
    # Use standard psycopg2 driver if available
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")

connect_args = {}
if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True
    )
    # Test connection
    with engine.connect() as conn:
        logger.info(f"Connected to database successfully using: {engine.url.drivername}")
except Exception as e:
    logger.warning(f"Could not connect to configured DB ({db_url}): {e}. Falling back to SQLite local database.")
    engine = create_engine(
        "sqlite:///./agentbid.db",
        connect_args={"check_same_thread": False},
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
