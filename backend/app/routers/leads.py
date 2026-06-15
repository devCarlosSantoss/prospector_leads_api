import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import LeadFilter, LeadUpdate, LeadBatchUpdate
from app.services.lead_service import LeadService

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("")
async def list_leads(
    page: int = 1,
    page_size: int = 50,
    niche: str = None,
    city: str = None,
    source: str = None,
    quality: str = None,
    commercial_status: str = None,
    temperature: str = None,
    has_website: bool = None,
    contacted: bool = None,
    interested: bool = None,
    campaign_id: int = None,
    search: str = None,
    sort_by: str = "collected_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    filters = LeadFilter(
        page=page,
        page_size=page_size,
        niche=niche,
        city=city,
        source=source,
        quality=quality,
        commercial_status=commercial_status,
        temperature=temperature,
        has_website=has_website,
        contacted=contacted,
        interested=interested,
        campaign_id=campaign_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    service = LeadService(db)
    return service.list_leads(filters)


@router.get("/stats")
async def get_stats(campaign_id: int = None, db: Session = Depends(get_db)):
    service = LeadService(db)
    return service.get_stats(campaign_id)


@router.get("/{lead_id}")
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


@router.post("")
async def create_lead(data: dict, db: Session = Depends(get_db)):
    service = LeadService(db)
    result = service.create_lead(data)
    if result.get("duplicate"):
        raise HTTPException(status_code=409, detail=result["message"])
    return result


@router.put("/{lead_id}")
async def update_lead(lead_id: int, updates: LeadUpdate, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.update_lead(lead_id, updates)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    service = LeadService(db)
    if not service.delete_lead(lead_id):
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    return {"message": "Lead removido"}


@router.post("/batch")
async def batch_update(updates: LeadBatchUpdate, db: Session = Depends(get_db)):
    service = LeadService(db)
    count = service.batch_update(updates.lead_ids, updates.updates)
    return {"updated": count, "message": f"{count} leads atualizados"}


@router.post("/import")
async def import_leads(
    file: UploadFile = File(...),
    campaign_id: int = Form(None),
    db: Session = Depends(get_db),
):
    import csv
    import io

    content = await file.read()
    text = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    leads_data = []
    for row in reader:
        leads_data.append(row)

    if not leads_data:
        raise HTTPException(status_code=400, detail="Nenhum dado encontrado no arquivo")

    service = LeadService(db)
    count = service.import_leads(leads_data, campaign_id)
    return {"imported": count, "message": f"{count} leads importados"}
