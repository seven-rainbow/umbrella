from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db.clickhouse import ClickHouseRepository, get_repository
from app.models.assessment import AssessmentJobResponse, VolatileDomainsResponse
from app.services.assessment import AssessmentOrchestrator
from app.services.model_config import ModelConfigService
from app.services.volatility import VolatilityService

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/volatile-domains", response_model=VolatileDomainsResponse)
def list_volatile_domains(
    snapshot_date: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=100, ge=1, le=500),
    repository: ClickHouseRepository = Depends(get_repository),
) -> VolatileDomainsResponse:
    return VolatilityService(repository).list_volatile_domains(snapshot_date, limit)


@router.get("/jobs/{job_id}", response_model=AssessmentJobResponse)
def get_assessment_job(
    job_id: str,
    repository: ClickHouseRepository = Depends(get_repository),
) -> AssessmentJobResponse:
    service = AssessmentOrchestrator(repository, ModelConfigService(repository))
    return service.get_job(job_id)
