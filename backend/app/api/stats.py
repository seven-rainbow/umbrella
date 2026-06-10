from fastapi import APIRouter, Depends

from app.db.clickhouse import ClickHouseRepository, get_repository
from app.models.stats import CurrentTopDomainsResponse, DatasetOverviewResponse
from app.services.stats import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=DatasetOverviewResponse)
def get_dataset_overview(
    repository: ClickHouseRepository = Depends(get_repository),
) -> DatasetOverviewResponse:
    return StatsService(repository).get_dataset_overview()


@router.get("/current-top-domains", response_model=CurrentTopDomainsResponse)
def get_current_top_domains(
    repository: ClickHouseRepository = Depends(get_repository),
) -> CurrentTopDomainsResponse:
    return StatsService(repository).get_current_top_domains(limit=100)
