import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.models import Lead, Campaign, SearchHistory
from app.schemas import LeadFilter, LeadUpdate


class LeadService:
    def __init__(self, db: Session):
        self.db = db

    def list_leads(self, filters: LeadFilter) -> dict:
        query = self.db.query(Lead)

        if filters.niche:
            query = query.filter(Lead.niche.ilike(f"%{filters.niche}%"))
        if filters.city:
            query = query.filter(Lead.city.ilike(f"%{filters.city}%"))
        if filters.source:
            query = query.filter(Lead.source == filters.source)
        if filters.quality:
            query = query.filter(Lead.quality == filters.quality)
        if filters.commercial_status:
            query = query.filter(Lead.commercial_status == filters.commercial_status)
        if filters.temperature:
            query = query.filter(Lead.temperature == filters.temperature)
        if filters.has_website is not None:
            query = query.filter(Lead.has_website == filters.has_website)
        if filters.contacted is not None:
            query = query.filter(Lead.contacted == filters.contacted)
        if filters.interested is not None:
            query = query.filter(Lead.interested == filters.interested)
        if filters.campaign_id:
            query = query.filter(Lead.campaign_id == filters.campaign_id)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Lead.company_name.ilike(search_term),
                    Lead.phone.ilike(search_term),
                    Lead.email.ilike(search_term),
                    Lead.instagram.ilike(search_term),
                    Lead.lead_city.ilike(search_term),
                    Lead.niche.ilike(search_term),
                )
            )

        # Sort
        sort_col = getattr(Lead, filters.sort_by, Lead.collected_at)
        if filters.sort_order == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        total = query.count()
        page = filters.page
        page_size = filters.page_size
        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        leads = query.offset(offset).limit(page_size).all()

        return {
            "leads": [self._lead_to_dict(l) for l in leads],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_lead(self, lead_id: int) -> Optional[dict]:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        return self._lead_to_dict(lead) if lead else None

    def get_all_leads(self) -> list:
        return self.db.query(Lead).all()

    def update_lead(self, lead_id: int, updates: LeadUpdate) -> Optional[dict]:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None

        update_data = updates.model_dump(exclude_unset=True)

        # Handle date fields
        date_fields = ["follow_up_date", "first_contact_date", "last_contact_date"]
        for field in date_fields:
            if field in update_data and isinstance(update_data[field], str):
                try:
                    update_data[field] = datetime.fromisoformat(update_data[field].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    update_data[field] = None

        for key, value in update_data.items():
            setattr(lead, key, value)

        self.db.commit()
        self.db.refresh(lead)
        return self._lead_to_dict(lead)

    def batch_update(self, lead_ids: list[int], updates: LeadUpdate) -> int:
        count = 0
        for lid in lead_ids:
            result = self.update_lead(lid, updates)
            if result:
                count += 1
        return count

    def delete_lead(self, lead_id: int) -> bool:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        self.db.delete(lead)
        self.db.commit()
        return True

    def get_stats(self, campaign_id: Optional[int] = None) -> dict:
        query = self.db.query(Lead)
        if campaign_id:
            query = query.filter(Lead.campaign_id == campaign_id)

        total = query.count()
        contacted = query.filter(Lead.contacted == True).count()
        responded = query.filter(Lead.lead_response != "").count()
        interested = query.filter(Lead.interested == True).count()
        closed = query.filter(Lead.commercial_status == "fechado").count()
        refused = query.filter(Lead.refused == True).count()
        proposals = query.filter(Lead.proposal_sent == True).count()
        with_website = query.filter(Lead.has_website == True).count()
        without_website = query.filter(Lead.has_website == False).count()
        hot = query.filter(Lead.quality == "quente").count()
        warm = query.filter(Lead.quality == "morno").count()
        cold = query.filter(Lead.quality == "frio").count()

        # Status distribution
        status_counts = {}
        for status in ["novo", "não contatado", "contato iniciado", "aguardando resposta",
                        "respondeu", "interessado", "reunião marcada", "proposta enviada",
                        "negociação", "fechado", "recusado", "sem retorno", "lead inválido"]:
            count = query.filter(Lead.commercial_status == status).count()
            if count > 0:
                status_counts[status] = count

        return {
            "total_leads": total,
            "contacted": contacted,
            "responded": responded,
            "interested": interested,
            "closed": closed,
            "refused": refused,
            "proposals_sent": proposals,
            "with_website": with_website,
            "without_website": without_website,
            "hot_leads": hot,
            "warm_leads": warm,
            "cold_leads": cold,
            "conversion_rate": round((closed / total * 100), 1) if total > 0 else 0,
            "status_distribution": status_counts,
        }

    def create_lead(self, data: dict) -> dict:
        from app.processors.deduplicator import Deduplicator
        dedup = Deduplicator()
        existing = self.db.query(Lead).all()
        is_dup, match = dedup.is_duplicate_against_db(data, existing)
        if is_dup:
            return {"duplicate": True, "existing_id": match.id, "message": "Lead já existe no banco"}

        lead = Lead(**{k: v for k, v in data.items() if hasattr(Lead, k)})
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return self._lead_to_dict(lead)

    def import_leads(self, leads_data: list[dict], campaign_id: Optional[int] = None) -> int:
        from app.processors.deduplicator import Deduplicator
        dedup = Deduplicator()
        existing = self.db.query(Lead).all()
        count = 0
        for data in leads_data:
            is_dup, _ = dedup.is_duplicate_against_db(data, existing)
            if is_dup:
                continue
            lead = Lead(**data)
            if campaign_id:
                lead.campaign_id = campaign_id
            self.db.add(lead)
            count += 1
            existing.append(lead)
        self.db.commit()
        return count

    def _lead_to_dict(self, lead: Lead) -> dict:
        if not lead:
            return {}
        result = {}
        for column in lead.__table__.columns:
            value = getattr(lead, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result


class CampaignService:
    def __init__(self, db: Session):
        self.db = db

    def list_campaigns(self) -> list[dict]:
        campaigns = self.db.query(Campaign).order_by(desc(Campaign.created_at)).all()
        result = []
        for c in campaigns:
            data = self._campaign_to_dict(c)
            data["lead_count"] = self.db.query(Lead).filter(Lead.campaign_id == c.id).count()
            result.append(data)
        return result

    def create_campaign(self, name: str, niche: str, city: str, notes: str = "") -> dict:
        campaign = Campaign(
            name=name,
            niche=niche,
            city=city,
            notes=notes,
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return self._campaign_to_dict(campaign)

    def get_campaign(self, campaign_id: int) -> Optional[dict]:
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return None
        data = self._campaign_to_dict(campaign)
        data["lead_count"] = self.db.query(Lead).filter(Lead.campaign_id == campaign_id).count()
        return data

    def update_campaign(self, campaign_id: int, updates: dict) -> Optional[dict]:
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(campaign, key, value)
        self.db.commit()
        self.db.refresh(campaign)
        return self._campaign_to_dict(campaign)

    def delete_campaign(self, campaign_id: int) -> bool:
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return False
        self.db.delete(campaign)
        self.db.commit()
        return True

    def _campaign_to_dict(self, campaign: Campaign) -> dict:
        if not campaign:
            return {}
        result = {}
        for column in campaign.__table__.columns:
            value = getattr(campaign, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result


class SearchHistoryService:
    def __init__(self, db: Session):
        self.db = db

    def create_search(self, niche: str, city: str, sources: list[str], campaign_id: Optional[int] = None, country: str = "Brasil") -> SearchHistory:
        search = SearchHistory(
            niche=niche,
            city=city,
            country=country,
            sources_used=json.dumps(sources),
            status="running",
            campaign_id=campaign_id,
        )
        self.db.add(search)
        self.db.commit()
        self.db.refresh(search)
        return search

    def complete_search(self, search_id: int, leads_found: int, error_log: str = ""):
        search = self.db.query(SearchHistory).filter(SearchHistory.id == search_id).first()
        if search:
            search.status = "completed" if not error_log else "completed_with_errors"
            search.leads_found = leads_found
            search.completed_at = datetime.now(timezone.utc)
            search.error_log = error_log
            self.db.commit()

    def fail_search(self, search_id: int, error: str):
        search = self.db.query(SearchHistory).filter(SearchHistory.id == search_id).first()
        if search:
            search.status = "failed"
            search.error_log = error
            search.completed_at = datetime.now(timezone.utc)
            self.db.commit()

    def get_search(self, search_id: int) -> Optional[dict]:
        search = self.db.query(SearchHistory).filter(SearchHistory.id == search_id).first()
        if not search:
            return None
        data = {}
        for column in search.__table__.columns:
            value = getattr(search, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[column.name] = value
        return data

    def list_history(self, limit: int = 50) -> list[dict]:
        searches = self.db.query(SearchHistory).order_by(desc(SearchHistory.started_at)).limit(limit).all()
        result = []
        for s in searches:
            data = {}
            for column in s.__table__.columns:
                value = getattr(s, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                data[column.name] = value
            result.append(data)
        return result
