"""AI Usage tracking model."""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(100), nullable=False, index=True)  # e.g. 'chat', 'mockup', 'audit-analysis'
    model = Column(String(100), default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)  # Estimated cost in USD
    lead_id = Column(Integer, nullable=True, index=True)  # Optional FK to lead
    created_at = Column(DateTime, server_default=func.now(), index=True)
