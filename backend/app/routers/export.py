from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lead
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["export"])


def _get_leads(db: Session, campaign_id: int = None, quality: str = None, status: str = None):
    query = db.query(Lead)
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    if quality:
        query = query.filter(Lead.quality == quality)
    if status:
        query = query.filter(Lead.commercial_status == status)
    return query.order_by(Lead.collected_at.desc()).all()


@router.get("/excel")
async def export_excel(
    campaign_id: int = None,
    quality: str = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    leads = _get_leads(db, campaign_id, quality, status)
    service = ExportService()
    excel_bytes = service.export_excel(leads)

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=leads_prospeccao.xlsx"},
    )


@router.get("/csv")
async def export_csv(
    campaign_id: int = None,
    quality: str = None,
    status: str = None,
    db: Session = Depends(get_db),
):
    leads = _get_leads(db, campaign_id, quality, status)
    service = ExportService()
    csv_content = service.export_csv(leads)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=leads_prospeccao.csv"},
    )
