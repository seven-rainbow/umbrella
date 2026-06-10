from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db.clickhouse import ClickHouseRepository, get_repository
from app.models.activity import ActivityResponse
from app.services.activity import ActivityService

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("/{domain}/activity", response_model=ActivityResponse)
def get_domain_activity(
    domain: str,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    repository: ClickHouseRepository = Depends(get_repository),
) -> ActivityResponse:
    service = ActivityService(repository)
    return service.get_activity(domain=domain, from_date=from_date, to_date=to_date)

