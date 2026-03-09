"""Setting model for app configuration."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, default="")
    is_encrypted = Column(Boolean, default=False)
    category = Column(String(100), default="general")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
