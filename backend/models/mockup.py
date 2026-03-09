"""Mockup model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Mockup(Base):
    __tablename__ = "mockups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    html_path = Column(Text, default="")
    screenshot_path = Column(Text, default="")
    template_name = Column(String(100), default="")
    ai_prompt_used = Column(Text, default="")
    version = Column(Integer, default=1)
    customizations = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
