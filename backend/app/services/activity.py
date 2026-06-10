from __future__ import annotations

import re
from datetime import date, timedelta

from fastapi import HTTPException

from app.core.config import get_settings
from app.db.clickhouse import RankRepository
from app.models.activity import ActivityPoint, ActivityResponse, ActivitySummary

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
TOP_N = 1_000_000


def normalize_domain(domain: str) -> str:
    normalized = domain.strip().lower().rstrip(".")
    if not DOMAIN_RE.match(normalized):
        raise HTTPException(status_code=422, detail="Invalid domain")
    return normalized


def active_score(rank: int | None) -> float | None:
    if rank is None:
        return None
    return round(1 - ((rank - 1) / TOP_N), 6)


def iter_date_range(from_date: date, to_date: date):
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


class ActivityService:
    def __init__(self, repository: RankRepository):
        self.repository = repository

    def get_activity(self, domain: str, from_date: date, to_date: date) -> ActivityResponse:
        settings = get_settings()
        normalized_domain = normalize_domain(domain)

        if from_date > to_date:
            raise HTTPException(status_code=422, detail="from must be earlier than or equal to to")

        total_days = (to_date - from_date).days + 1
        if total_days > settings.max_query_days:
            raise HTTPException(status_code=422, detail=f"Date range cannot exceed {settings.max_query_days} days")

        rows = self.repository.fetch_domain_ranks(normalized_domain, from_date, to_date)
        rank_by_date = {row_date: rank for row_date, rank in rows}

        series = [
            ActivityPoint(date=day, rank=rank_by_date.get(day), active_score=active_score(rank_by_date.get(day)))
            for day in iter_date_range(from_date, to_date)
        ]
        ranks = [point.rank for point in series if point.rank is not None]

        summary = ActivitySummary(
            days_seen=len(ranks),
            total_days=total_days,
            coverage_ratio=round(len(ranks) / total_days, 3),
            best_rank=min(ranks) if ranks else None,
            worst_rank=max(ranks) if ranks else None,
            avg_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
        )
        return ActivityResponse(
            domain=normalized_domain,
            from_date=from_date,
            to_date=to_date,
            summary=summary,
            series=series,
        )

