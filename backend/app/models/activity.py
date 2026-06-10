from datetime import date

from pydantic import BaseModel, Field


class ActivityPoint(BaseModel):
    date: date
    rank: int | None
    active_score: float | None


class ActivitySummary(BaseModel):
    days_seen: int
    total_days: int
    coverage_ratio: float
    best_rank: int | None
    worst_rank: int | None
    avg_rank: float | None


class ActivityResponse(BaseModel):
    domain: str
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    summary: ActivitySummary
    series: list[ActivityPoint]

    model_config = {"populate_by_name": True}

