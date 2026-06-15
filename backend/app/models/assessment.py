from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high", "unknown"]
JobStatus = Literal["pending", "running", "success", "failed"]


class AssessmentRequest(BaseModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    mode: str = "quick"
    model_id: str | None = None

    model_config = {"populate_by_name": True}


class AssessmentEvidence(BaseModel):
    latest_rank: int | None = None
    best_rank: int | None = None
    worst_rank: int | None = None
    coverage_ratio: float
    volatility_score: float
    rank_delta_1d: int | None = None
    rank_delta_7d: int | None = None
    rank_delta_30d: int | None = None


class AssessmentModelInfo(BaseModel):
    provider: str
    model: str


class AssessmentReport(BaseModel):
    risk_level: RiskLevel
    confidence: float
    summary: str
    key_findings: list[str]
    recommended_actions: list[str]
    evidence: AssessmentEvidence
    model: AssessmentModelInfo


class AssessmentResponse(BaseModel):
    job_id: str
    status: JobStatus
    domain: str
    report: AssessmentReport | None = None
    error_message: str | None = None


class AssessmentJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    domain: str
    report: AssessmentReport | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DomainAssessmentHistoryItem(BaseModel):
    job_id: str
    created_at: datetime | None = None
    report: AssessmentReport


class DomainAssessmentHistoryResponse(BaseModel):
    domain: str
    reports: list[DomainAssessmentHistoryItem]


class VolatileDomain(BaseModel):
    domain: str
    latest_rank: int
    rank_delta_1d: int | None = None
    rank_delta_7d: int | None = None
    rank_delta_30d: int | None = None
    percentile_shift: float
    is_new_entry: bool
    is_disappeared: bool
    volatility_score: float
    reason: str


class VolatileDomainsResponse(BaseModel):
    snapshot_date: date | None
    domains: list[VolatileDomain]


class DomainAssessmentContext(BaseModel):
    domain: str
    from_date: date
    to_date: date
    latest_rank: int | None
    best_rank: int | None
    worst_rank: int | None
    avg_rank: float | None
    coverage_ratio: float
    total_days: int
    days_seen: int
    rank_delta_1d: int | None
    rank_delta_7d: int | None
    rank_delta_30d: int | None
    volatility_score: float
    is_new_entry: bool
    facts: list[str]

    def prompt_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
