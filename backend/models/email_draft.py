"""EmailDraft model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    mockup_id = Column(Integer, ForeignKey("mockups.id"), nullable=True)
    subject = Column(String(500), default="")
    body_html = Column(Text, default="")
    body_text = Column(Text, default="")
    recipient_email = Column(String(255), default="")
    tone = Column(String(50), default="professional")
    pricing_tier_shown = Column(String(50), default="all")
    status = Column(String(50), default="draft", index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
