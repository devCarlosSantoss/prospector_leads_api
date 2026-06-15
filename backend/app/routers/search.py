import asyncio
import json
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SearchRequest
from app.models import Lead, SearchHistory
from app.services.lead_service import LeadService, CampaignService, SearchHistoryService
from app.processors.deduplicator import Deduplicator
from app.processors.scorer import LeadScorer
from app.processors.enricher import LeadEnricher

router = APIRouter(prefix="/api/search", tags=["search"])

COLLECTOR_REGISTRY = {}


def register_collector(name: str, collector_class):
    COLLECTOR_REGISTRY[name] = collector_class


async def run_search_task(
    search_id: int,
    niche: str,
    city: str,
    sources: list[str],
    campaign_id: int | None,
    db: Session,
    country: str = "Brasil",
    max_results: int = 50,
):
    search_svc = SearchHistoryService(db)
    lead_svc = LeadService(db)
    dedup = Deduplicator()
    scorer = LeadScorer()
    enricher = LeadEnricher()

    all_results = []
    errors = []

    for source_name in sources:
        collector_cls = COLLECTOR_REGISTRY.get(source_name)
        if not collector_cls:
            errors.append(f"Fonte '{source_name}' não encontrada")
            continue

        try:
            collector = collector_cls()
            results = await collector.collect(niche, city, country=country, max_results=max_results)
            all_results.extend(results)
            if hasattr(collector, "errors") and collector.errors:
                errors.extend(collector.errors)
        except Exception as e:
            errors.append(f"Erro na fonte {source_name}: {str(e)[:200]}")
            continue

    # Deduplicate in-memory
    all_results = dedup.deduplicate(all_results)

    # Deduplicate against existing DB
    existing_db_leads = lead_svc.get_all_leads()
    db_filtered = []
    for result in all_results:
        is_dup, _ = dedup.is_duplicate_against_db(result, existing_db_leads)
        if not is_dup:
            db_filtered.append(result)
    all_results = db_filtered

    # Enrich and score each lead
    enriched_count = 0
    for result in all_results:
        try:
            result = await enricher.enrich(result)
            enriched_count += 1
        except Exception:
            pass

        scoring = scorer.score(result)
        result.update(scoring)

        result["niche"] = niche
        result["city"] = city
        result["country"] = country
        result["collected_at"] = datetime.now(timezone.utc).isoformat()
        result["campaign_id"] = campaign_id

    # Save to database
    leads_to_save = []
    for result in all_results:
        try:
            lead = Lead(
                campaign_id=result.get("campaign_id"),
                collected_at=datetime.now(timezone.utc),
                niche=niche,
                city=city,
                country=str(result.get("country", "Brasil"))[:100],
                company_name=str(result.get("company_name", ""))[:255],
                category=str(result.get("category", ""))[:255],
                description=str(result.get("description", ""))[:1000],
                website=str(result.get("website", ""))[:500],
                website_status=str(result.get("website_status", ""))[:50],
                phone=str(result.get("phone", ""))[:100],
                whatsapp_link=str(result.get("whatsapp_link", ""))[:500],
                email=str(result.get("email", ""))[:255],
                instagram=str(result.get("instagram", ""))[:500],
                facebook=str(result.get("facebook", ""))[:500],
                address=str(result.get("address", ""))[:500],
                neighborhood=str(result.get("neighborhood", ""))[:255],
                lead_city=str(result.get("lead_city", ""))[:255],
                state=str(result.get("state", ""))[:50],
                zipcode=str(result.get("zipcode", ""))[:20],
                source=str(result.get("source", ""))[:100],
                source_url=str(result.get("source_url", ""))[:500],
                quality=str(result.get("quality", ""))[:50],
                score=result.get("score", 0) or 0,
                score_reason=str(result.get("score_reason", ""))[:1000],
                has_website=bool(result.get("has_website")),
                has_landing_page=bool(result.get("has_landing_page")),
                has_whatsapp=bool(result.get("has_whatsapp") or result.get("phone")),
                instagram_active=bool(result.get("instagram_active")),
                auto_notes=str(result.get("auto_notes", ""))[:1000],
                opportunity=str(result.get("opportunity", ""))[:500],
                suggested_service=str(result.get("suggested_service", ""))[:500],
                next_action=str(result.get("next_action", ""))[:500],
                commercial_status="novo",
                temperature="frio",
            )
            leads_to_save.append(lead)
        except Exception as e:
            errors.append(f"Erro ao salvar lead '{result.get('company_name', '')}': {str(e)[:100]}")

    # Batch save
    if leads_to_save:
        db.bulk_save_objects(leads_to_save)
        db.commit()

    # Update search history
    error_text = "; ".join(errors[:10])
    search_svc.complete_search(search_id, len(leads_to_save), error_text)


@router.post("")
async def start_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    search_svc = SearchHistoryService(db)
    search = search_svc.create_search(
        niche=request.niche,
        city=request.city,
        sources=request.sources,
        campaign_id=request.campaign_id,
        country=request.country,
    )

    background_tasks.add_task(
        run_search_task,
        search.id,
        request.niche,
        request.city,
        request.sources,
        request.campaign_id,
        db,
        request.country,
        request.max_results,
    )

    return {
        "search_id": search.id,
        "status": "running",
        "message": "Busca iniciada em segundo plano",
    }


@router.get("/{search_id}")
async def get_search_status(search_id: int, db: Session = Depends(get_db)):
    search_svc = SearchHistoryService(db)
    search = search_svc.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Busca não encontrada")
    return search


@router.get("")
async def list_search_history(db: Session = Depends(get_db)):
    search_svc = SearchHistoryService(db)
    return search_svc.list_history()
