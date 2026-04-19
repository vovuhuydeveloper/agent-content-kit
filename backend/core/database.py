"""
Database configuration
Database connection, session management, and dependency injection
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.base import Base

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///autoclip.db"
)

# If nosetenvironment variable，useconfigurationfunctionGet database URL
if DATABASE_URL == "sqlite:///autoclip.db":
    try:
        from .config import get_database_url
        DATABASE_URL = get_database_url()
    except ImportError:
        # If import fails, keep defaults
        pass

# createdataengine
if "sqlite" in DATABASE_URL:
    # SQLiteconfiguration
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        },
        poolclass=StaticPool,
        pool_pre_ping=True,
        echo=False  # Set True to see SQL statements
    )
else:
    # PostgreSQLconfiguration
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency injection
    For FastAPI dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)

def reset_database():
    """Reset database"""
    drop_tables()
    create_tables()

from sqlalchemy import text


def test_connection() -> bool:
    """Test database connection"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).fetchone()
        return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

# Database initialization
def init_database():
    """initialize database"""
    print("Initializing database...")

    # Test connection
    if not test_connection():
        print("❌ Database connection failed")
        return False

    # Create tables
    try:
        create_tables()
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Database table creation failed: {e}")
        return False

if __name__ == "__main__":
    # fileinitialize database
    init_database()
