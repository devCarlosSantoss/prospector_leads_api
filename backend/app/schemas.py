from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    niche: str
    city: str
    country: str = "Brasil"
    campaign_id: Optional[int] = None
    sources: list[str] = ["google_maps", "duckduckgo"]
    max_results: int = 50


class SearchResponse(BaseModel):
    search_id: int
    status: str
    message: str


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    website_status: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_link: Optional[str] = None
    email: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    lead_city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    quality: Optional[str] = None
    score: Optional[int] = None
    score_reason: Optional[str] = None
    has_website: Optional[bool] = None
    has_landing_page: Optional[bool] = None
    has_whatsapp: Optional[bool] = None
    instagram_active: Optional[bool] = None
    auto_notes: Optional[str] = None
    opportunity: Optional[str] = None
    suggested_service: Optional[str] = None
    suggested_message: Optional[str] = None
    next_action: Optional[str] = None
    commercial_status: Optional[str] = None
    contacted: Optional[bool] = None
    lead_response: Optional[str] = None
    refused: Optional[bool] = None
    refusal_reason: Optional[str] = None
    interested: Optional[bool] = None
    follow_up_scheduled: Optional[bool] = None
    follow_up_date: Optional[str] = None
    proposal_sent: Optional[bool] = None
    estimated_value: Optional[float] = None
    possible_close: Optional[bool] = None
    manual_notes: Optional[str] = None
    owner_identified: Optional[bool] = None
    owner_name: Optional[str] = None
    spoke_with: Optional[str] = None
    contact_channel: Optional[str] = None
    temperature: Optional[str] = None
    tags: Optional[str] = None
    first_contact_date: Optional[str] = None
    last_contact_date: Optional[str] = None


class LeadBatchUpdate(BaseModel):
    lead_ids: list[int]
    updates: LeadUpdate


class CampaignCreate(BaseModel):
    name: str
    niche: str
    city: str
    notes: str = ""


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class LeadFilter(BaseModel):
    niche: Optional[str] = None
    city: Optional[str] = None
    source: Optional[str] = None
    quality: Optional[str] = None
    commercial_status: Optional[str] = None
    temperature: Optional[str] = None
    has_website: Optional[bool] = None
    contacted: Optional[bool] = None
    interested: Optional[bool] = None
    campaign_id: Optional[int] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 50
    sort_by: str = "collected_at"
    sort_order: str = "desc"
