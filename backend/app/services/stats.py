from app.db.clickhouse import RankRepository
from app.models.stats import CurrentTopDomainsResponse, DatasetOverviewResponse, TopDomainItem


class StatsService:
    def __init__(self, repository: RankRepository):
        self.repository = repository

    def get_dataset_overview(self) -> DatasetOverviewResponse:
        min_date, max_date, snapshot_days, total_rows, latest_imported_at = self.repository.fetch_dataset_overview()
        return DatasetOverviewResponse(
            min_date=min_date,
            max_date=max_date,
            snapshot_days=snapshot_days,
            total_rows=total_rows,
            latest_imported_at=latest_imported_at,
        )

    def get_current_top_domains(self, limit: int = 100) -> CurrentTopDomainsResponse:
        snapshot_date, rows = self.repository.fetch_current_top_domains(limit=limit)
        return CurrentTopDomainsResponse(
            snapshot_date=snapshot_date,
            domains=[TopDomainItem(rank=rank, domain=domain) for rank, domain in rows],
        )
