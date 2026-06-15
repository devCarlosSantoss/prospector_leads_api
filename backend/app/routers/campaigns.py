from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CampaignCreate, CampaignUpdate
from app.services.lead_service import CampaignService

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("")
async def list_campaigns(db: Session = Depends(get_db)):
    service = CampaignService(db)
    return service.list_campaigns()


@router.post("")
async def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)):
    service = CampaignService(db)
    return service.create_campaign(data.name, data.niche, data.city, data.notes)


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    service = CampaignService(db)
    campaign = service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, data: CampaignUpdate, db: Session = Depends(get_db)):
    service = CampaignService(db)
    campaign = service.update_campaign(campaign_id, data.model_dump(exclude_unset=True))
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    service = CampaignService(db)
    if not service.delete_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return {"message": "Campanha removida"}
