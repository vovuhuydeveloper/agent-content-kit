"""
Base model — Foundation for all SQLAlchemy models.
Provides id, timestamps, and uuid generation.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import DeclarativeBase


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass


class TimestampMixin:
    """Mixin adding created_at / updated_at columns"""
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)


class BaseModel(Base):
    """Base model with id + timestamps"""
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
