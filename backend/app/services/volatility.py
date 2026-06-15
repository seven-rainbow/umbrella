from __future__ import annotations

from datetime import date
from typing import Protocol

from app.models.assessment import VolatileDomain, VolatileDomainsResponse


class VolatilityRepository(Protocol):
    def fetch_volatile_domains(self, snapshot_date: date | None, limit: int = 100) -> tuple[date | None, list[dict]]:
        ...


def volatility_score(
    latest_rank: int | None,
    rank_delta_7d: int | None,
    rank_delta_30d: int | None,
    is_new_entry: bool = False,
) -> float:
    if latest_rank is None:
        return 0
    components = [0.0]
    if rank_delta_7d is not None:
        components.append(min(1, abs(rank_delta_7d) / 100_000))
    if rank_delta_30d is not None:
        components.append(min(1, abs(rank_delta_30d) / 300_000))
    if is_new_entry:
        components.append(0.8 if latest_rank > 100_000 else 0.9)
    return round(max(components), 3)


def volatility_reason(latest_rank: int, rank_delta_7d: int | None, rank_delta_30d: int | None, is_new_entry: bool) -> str:
    if is_new_entry and latest_rank <= 100_000:
        return "new top-100k entry"
    if is_new_entry:
        return "new top-1m entry within 30 days"
    if rank_delta_7d is not None and rank_delta_7d <= -10_000:
        return "7-day rank surge"
    if rank_delta_7d is not None and rank_delta_7d >= 10_000:
        return "7-day rank drop"
    if rank_delta_30d is not None and abs(rank_delta_30d) >= 10_000:
        return "30-day rank movement"
    return "rank volatility"


class VolatilityService:
    def __init__(self, repository: VolatilityRepository):
        self.repository = repository

    def list_volatile_domains(self, snapshot_date: date | None = None, limit: int = 100) -> VolatileDomainsResponse:
        actual_date, rows = self.repository.fetch_volatile_domains(snapshot_date, limit)
        return VolatileDomainsResponse(snapshot_date=actual_date, domains=[VolatileDomain(**row) for row in rows])
