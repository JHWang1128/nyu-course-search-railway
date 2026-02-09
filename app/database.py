import os
from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/nyucourses")
# Railway uses postgres:// but SQLAlchemy needs postgresql+psycopg:// (psycopg3)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Fix empty port issue (Railway sometimes provides host:/db with empty port)
parsed = urlparse(DATABASE_URL)
if parsed.hostname and not parsed.port:
    # Rebuild netloc without the trailing colon
    netloc = parsed.hostname
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        netloc = f"{userinfo}@{netloc}"
    DATABASE_URL = urlunparse(parsed._replace(netloc=netloc))

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_extensions():
    """Auto-create pgvector extension and HNSW index if they don't exist."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("pgvector extension ready")
    except Exception as e:
        print(f"Warning: Could not create pgvector extension: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

