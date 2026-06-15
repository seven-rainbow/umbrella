from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import Protocol

from fastapi import HTTPException
from pydantic import ValidationError

from app.models.assessment import (
    AssessmentEvidence,
    AssessmentJobResponse,
    AssessmentReport,
    AssessmentRequest,
    AssessmentResponse,
    DomainAssessmentContext,
    DomainAssessmentHistoryItem,
    DomainAssessmentHistoryResponse,
)
from app.models.model_config import ChatMessage
from app.services.activity import active_score, normalize_domain
from app.services.llm_gateway import LLMGateway
from app.services.model_config import ModelConfigService
from app.services.volatility import volatility_score


class AssessmentRepository(Protocol):
    def fetch_domain_ranks(self, domain: str, from_date: date, to_date: date) -> list[tuple[date, int]]:
        ...

    def record_assessment_job(self, job_id: str, domain: str, status: str, model_id: str = "", error_message: str = "") -> None:
        ...

    def insert_assessment_report(self, report: dict) -> None:
        ...

    def fetch_assessment_job(self, job_id: str) -> dict | None:
        ...

    def fetch_assessment_report_by_job(self, job_id: str) -> dict | None:
        ...

    def fetch_domain_assessment_reports(self, domain: str, limit: int = 20) -> list[dict]:
        ...


def _rank_on_or_before(rank_by_date: dict[date, int], target: date) -> int | None:
    for offset in range(0, 4):
        rank = rank_by_date.get(target - timedelta(days=offset))
        if rank is not None:
            return rank
    return None


class DomainContextBuilder:
    def __init__(self, repository: AssessmentRepository):
        self.repository = repository

    def build(self, domain: str, from_date: date, to_date: date) -> DomainAssessmentContext:
        normalized_domain = normalize_domain(domain)
        if from_date > to_date:
            raise HTTPException(status_code=422, detail="from must be earlier than or equal to to")

        rows = self.repository.fetch_domain_ranks(normalized_domain, from_date, to_date)
        rank_by_date = {row_date: rank for row_date, rank in rows}
        total_days = (to_date - from_date).days + 1
        ranks = [rank for _, rank in rows]
        latest_rank = rows[-1][1] if rows else None
        latest_date = rows[-1][0] if rows else to_date
        rank_1d = _rank_on_or_before(rank_by_date, latest_date - timedelta(days=1))
        rank_7d = _rank_on_or_before(rank_by_date, latest_date - timedelta(days=7))
        rank_30d = _rank_on_or_before(rank_by_date, latest_date - timedelta(days=30))
        delta_1d = latest_rank - rank_1d if latest_rank is not None and rank_1d is not None else None
        delta_7d = latest_rank - rank_7d if latest_rank is not None and rank_7d is not None else None
        delta_30d = latest_rank - rank_30d if latest_rank is not None and rank_30d is not None else None
        is_new_entry = latest_rank is not None and rank_30d is None
        score = volatility_score(latest_rank, delta_7d, delta_30d, is_new_entry)
        coverage = round(len(ranks) / total_days, 3) if total_days else 0
        facts = [
            f"Latest rank: {latest_rank}" if latest_rank is not None else "Domain not seen in selected range",
            f"Coverage: {len(ranks)}/{total_days} days ({coverage})",
        ]
        if delta_7d is not None:
            facts.append(f"7-day rank delta: {delta_7d}")
        if delta_30d is not None:
            facts.append(f"30-day rank delta: {delta_30d}")
        if latest_rank is not None:
            facts.append(f"Latest active score: {active_score(latest_rank)}")

        return DomainAssessmentContext(
            domain=normalized_domain,
            from_date=from_date,
            to_date=to_date,
            latest_rank=latest_rank,
            best_rank=min(ranks) if ranks else None,
            worst_rank=max(ranks) if ranks else None,
            avg_rank=round(sum(ranks) / len(ranks), 2) if ranks else None,
            coverage_ratio=coverage,
            total_days=total_days,
            days_seen=len(ranks),
            rank_delta_1d=delta_1d,
            rank_delta_7d=delta_7d,
            rank_delta_30d=delta_30d,
            volatility_score=score,
            is_new_entry=is_new_entry,
            facts=facts,
        )


class AssessmentOrchestrator:
    def __init__(
        self,
        repository: AssessmentRepository,
        model_config_service: ModelConfigService,
        llm_gateway: LLMGateway | None = None,
    ):
        self.repository = repository
        self.context_builder = DomainContextBuilder(repository)
        self.model_config_service = model_config_service
        self.llm_gateway = llm_gateway or LLMGateway()

    def assess_domain(self, domain: str, request: AssessmentRequest) -> AssessmentResponse:
        context = self.context_builder.build(domain, request.from_date, request.to_date)
        runtime_config = self.model_config_service.get_runtime_config(request.model_id)
        job_id = str(uuid.uuid4())
        self.repository.record_assessment_job(job_id, context.domain, "running", runtime_config.model_id)
        try:
            report = self._run_llm_assessment(context, runtime_config)
            self._store_report(job_id, context.domain, report)
            self.repository.record_assessment_job(job_id, context.domain, "success", runtime_config.model_id)
            return AssessmentResponse(job_id=job_id, status="success", domain=context.domain, report=report)
        except Exception as exc:
            self.repository.record_assessment_job(job_id, context.domain, "failed", runtime_config.model_id, str(exc))
            raise

    def get_job(self, job_id: str) -> AssessmentJobResponse:
        job = self.repository.fetch_assessment_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Assessment job not found")
        report = self.repository.fetch_assessment_report_by_job(job_id)
        return AssessmentJobResponse(
            job_id=job["job_id"],
            status=job["status"],
            domain=job["domain"],
            error_message=job["error_message"] or None,
            created_at=job["created_at"],
            updated_at=job["updated_at"],
            report=self._parse_report(report["report_json"]) if report else None,
        )

    def list_domain_reports(self, domain: str, limit: int = 20) -> DomainAssessmentHistoryResponse:
        normalized_domain = normalize_domain(domain)
        items = [
            DomainAssessmentHistoryItem(
                job_id=row["job_id"],
                created_at=row["created_at"],
                report=self._parse_report(row["report_json"]),
            )
            for row in self.repository.fetch_domain_assessment_reports(normalized_domain, limit)
        ]
        return DomainAssessmentHistoryResponse(domain=normalized_domain, reports=items)

    def _run_llm_assessment(self, context: DomainAssessmentContext, runtime_config) -> AssessmentReport:
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are a domain ranking analyst. Use only the supplied structured facts. "
                    "Return JSON with risk_level, confidence, summary, key_findings, recommended_actions. "
                    "risk_level must be low, medium, high, or unknown."
                ),
            ),
            ChatMessage(
                role="user",
                content=json.dumps(
                    {
                        "task": "Assess whether the domain's Umbrella ranking activity looks unusual.",
                        "context": context.prompt_payload(),
                    },
                    ensure_ascii=True,
                ),
            ),
        ]
        raw = self.llm_gateway.chat_json(runtime_config, messages)
        evidence = AssessmentEvidence(
            latest_rank=context.latest_rank,
            best_rank=context.best_rank,
            worst_rank=context.worst_rank,
            coverage_ratio=context.coverage_ratio,
            volatility_score=context.volatility_score,
            rank_delta_1d=context.rank_delta_1d,
            rank_delta_7d=context.rank_delta_7d,
            rank_delta_30d=context.rank_delta_30d,
        )
        report_payload = {
            "risk_level": raw.get("risk_level", "unknown"),
            "confidence": raw.get("confidence", 0),
            "summary": raw.get("summary", "The model did not provide a summary."),
            "key_findings": raw.get("key_findings", context.facts),
            "recommended_actions": raw.get("recommended_actions", ["Review with additional intelligence sources."]),
            "evidence": evidence.model_dump(),
            "model": {"provider": runtime_config.provider_type, "model": runtime_config.model_name},
        }
        try:
            return AssessmentReport(**report_payload)
        except ValidationError as exc:
            raise HTTPException(status_code=502, detail="Model returned invalid assessment schema") from exc

    def _store_report(self, job_id: str, domain: str, report: AssessmentReport) -> None:
        payload = report.model_dump(mode="json")
        self.repository.insert_assessment_report(
            {
                "job_id": job_id,
                "domain": domain,
                "risk_level": report.risk_level,
                "confidence": report.confidence,
                "summary": report.summary,
                "key_findings": json.dumps(report.key_findings, ensure_ascii=True),
                "recommended_actions": json.dumps(report.recommended_actions, ensure_ascii=True),
                "evidence": report.evidence.model_dump_json(),
                "model_provider": report.model.provider,
                "model_name": report.model.model,
                "report_json": json.dumps(payload, ensure_ascii=True),
            }
        )

    def _parse_report(self, report_json: str) -> AssessmentReport:
        return AssessmentReport(**json.loads(report_json))
