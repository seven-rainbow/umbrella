from datetime import date, datetime

from pydantic import BaseModel


class DatasetOverviewResponse(BaseModel):
    min_date: date | None
    max_date: date | None
    snapshot_days: int
    total_rows: int
    latest_imported_at: datetime | None


class TopDomainItem(BaseModel):
    rank: int
    domain: str


class CurrentTopDomainsResponse(BaseModel):
    snapshot_date: date | None
    domains: list[TopDomainItem]
