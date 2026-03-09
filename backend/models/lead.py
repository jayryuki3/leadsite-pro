"""Lead and LeadDetail models."""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(String(255), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, default="")
    phone = Column(String(50), default="")
    email = Column(String(255), default="")
    website = Column(Text, default="")
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    category = Column(String(100), default="other", index=True)
    status = Column(String(50), default="new", index=True)
    lat = Column(Float, default=0.0)
    lng = Column(Float, default=0.0)
    photo_ref = Column(Text, default="")
    notes = Column(Text, default="")
    google_maps_url = Column(Text, default="")

    # Scoring
    audit_score = Column(Float, nullable=True)
    website_quality_score = Column(Integer, default=-1)
    opportunity_score = Column(Float, default=0.0)
    audit_details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LeadDetail(Base):
    __tablename__ = "lead_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    services = Column(JSON, default=list)
    hours = Column(JSON, default=dict)
    owner_name = Column(String(255), default="")
    top_reviews = Column(JSON, default=list)
    photos_local = Column(JSON, default=list)
    brand_colors = Column(JSON, default=list)
    logo_path = Column(Text, default="")
    yelp_url = Column(Text, default="")
    audit_data = Column(JSON, nullable=True)
    tech_stack = Column(JSON, nullable=True)
    ai_profile_summary = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
