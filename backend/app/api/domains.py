from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db.clickhouse import ClickHouseRepository, get_repository
from app.models.activity import ActivityResponse
from app.models.assessment import AssessmentRequest, AssessmentResponse, DomainAssessmentHistoryResponse
from app.services.activity import ActivityService
from app.services.assessment import AssessmentOrchestrator
from app.services.model_config import ModelConfigService

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


@router.post("/{domain}/assessment", response_model=AssessmentResponse)
def assess_domain(
    domain: str,
    request: AssessmentRequest,
    repository: ClickHouseRepository = Depends(get_repository),
) -> AssessmentResponse:
    service = AssessmentOrchestrator(repository, ModelConfigService(repository))
    return service.assess_domain(domain=domain, request=request)


@router.get("/{domain}/assessments", response_model=DomainAssessmentHistoryResponse)
def list_domain_assessments(
    domain: str,
    limit: int = Query(default=20, ge=1, le=100),
    repository: ClickHouseRepository = Depends(get_repository),
) -> DomainAssessmentHistoryResponse:
    service = AssessmentOrchestrator(repository, ModelConfigService(repository))
    return service.list_domain_reports(domain, limit)
