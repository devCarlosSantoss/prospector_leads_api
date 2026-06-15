from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    niche = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    status = Column(String(50), default="active")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    leads = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)

    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    niche = Column(String(255), default="")
    city = Column(String(255), default="")
    country = Column(String(100), default="Brasil")

    company_name = Column(String(255), index=True)
    category = Column(String(255), default="")
    description = Column(Text, default="")

    website = Column(String(500), default="")
    website_status = Column(String(50), default="")
    phone = Column(String(100), default="")
    whatsapp_link = Column(String(500), default="")
    email = Column(String(255), default="")
    instagram = Column(String(500), default="")
    facebook = Column(String(500), default="")

    address = Column(String(500), default="")
    neighborhood = Column(String(255), default="")
    lead_city = Column(String(255), default="")
    state = Column(String(50), default="")
    zipcode = Column(String(20), default="")

    source = Column(String(100), default="")
    source_url = Column(String(500), default="")

    quality = Column(String(50), default="")
    score = Column(Integer, default=0)
    score_reason = Column(Text, default="")

    has_website = Column(Boolean, default=False)
    has_landing_page = Column(Boolean, default=False)
    has_whatsapp = Column(Boolean, default=False)
    instagram_active = Column(Boolean, default=False)

    auto_notes = Column(Text, default="")
    opportunity = Column(String(500), default="")
    suggested_service = Column(String(500), default="")
    next_action = Column(String(500), default="")

    contacted = Column(Boolean, default=False)
    first_contact_date = Column(DateTime, nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    commercial_status = Column(String(50), default="novo")
    lead_response = Column(Text, default="")
    refused = Column(Boolean, default=False)
    refusal_reason = Column(Text, default="")
    interested = Column(Boolean, default=False)
    follow_up_scheduled = Column(Boolean, default=False)
    follow_up_date = Column(DateTime, nullable=True)
    proposal_sent = Column(Boolean, default=False)
    estimated_value = Column(Float, nullable=True)
    possible_close = Column(Boolean, default=False)
    manual_notes = Column(Text, default="")

    owner_identified = Column(Boolean, default=False)
    owner_name = Column(String(255), default="")
    spoke_with = Column(String(100), default="")
    contact_channel = Column(String(50), default="")
    temperature = Column(String(20), default="frio")
    tags = Column(String(500), default="")

    campaign = relationship("Campaign", back_populates="leads")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    niche = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    country = Column(String(100), default="Brasil")
    sources_used = Column(Text, default="[]")
    leads_found = Column(Integer, default=0)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")
    error_log = Column(Text, default="")
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
