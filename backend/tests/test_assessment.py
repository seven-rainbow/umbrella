from datetime import date, datetime

import pytest
from fastapi import HTTPException

from app.models.assessment import AssessmentRequest
from app.models.model_config import ModelRuntimeConfig
from app.services.assessment import AssessmentOrchestrator, DomainContextBuilder


class FakeRepository:
    def __init__(self):
        self.jobs = []
        self.reports = []

    def fetch_domain_ranks(self, domain, from_date, to_date):
        assert domain == "example.com"
        return [
            (date(2026, 5, 13), 80_000),
            (date(2026, 6, 5), 70_000),
            (date(2026, 6, 11), 40_000),
            (date(2026, 6, 12), 20_000),
        ]

    def record_assessment_job(self, job_id, domain, status, model_id="", error_message=""):
        self.jobs.append({"job_id": job_id, "domain": domain, "status": status, "error_message": error_message})

    def insert_assessment_report(self, report):
        self.reports.append(report)

    def fetch_assessment_job(self, job_id):
        return {
            "job_id": job_id,
            "domain": "example.com",
            "status": "success",
            "error_message": "",
            "model_id": "model-1",
            "created_at": datetime(2026, 6, 12),
            "updated_at": datetime(2026, 6, 12),
        }

    def fetch_assessment_report_by_job(self, job_id):
        return {"report_json": self.reports[0]["report_json"]}

    def fetch_domain_assessment_reports(self, domain, limit=20):
        return [{"job_id": self.reports[0]["job_id"], "report_json": self.reports[0]["report_json"], "created_at": None}]


class FakeModelConfigService:
    def get_runtime_config(self, model_id=None):
        return ModelRuntimeConfig(
            model_id="model-1",
            provider_id="provider-1",
            provider_name="OpenAI Compatible",
            provider_type="openai-compatible",
            base_url="https://models.example/v1",
            api_key="secret",
            model_name="gpt-test",
            temperature=0.2,
            max_tokens=1200,
            timeout_seconds=30,
        )


class EmptyModelConfigService:
    def get_runtime_config(self, model_id=None):
        raise HTTPException(status_code=400, detail="No default model configured")


class FakeGateway:
    def chat_json(self, config, messages):
        assert config.model_name == "gpt-test"
        assert "example.com" in messages[1].content
        return {
            "risk_level": "medium",
            "confidence": 0.76,
            "summary": "Ranking rose quickly.",
            "key_findings": ["7-day rise"],
            "recommended_actions": ["Review external intelligence"],
        }


class NonJsonGateway:
    def chat_json(self, config, messages):
        raise HTTPException(status_code=502, detail="Model returned non-JSON assessment")


def test_domain_context_builder_calculates_deltas_and_coverage():
    context = DomainContextBuilder(FakeRepository()).build("Example.COM", date(2026, 5, 13), date(2026, 6, 12))

    assert context.domain == "example.com"
    assert context.latest_rank == 20_000
    assert context.rank_delta_7d == -50_000
    assert context.rank_delta_30d == -60_000
    assert context.coverage_ratio == round(4 / 31, 3)
    assert context.volatility_score == 0.5


def test_assessment_orchestrator_stores_success_report_and_status_flow():
    repository = FakeRepository()
    response = AssessmentOrchestrator(repository, FakeModelConfigService(), FakeGateway()).assess_domain(
        "example.com",
        AssessmentRequest(from_date=date(2026, 5, 13), to_date=date(2026, 6, 12)),
    )

    assert response.status == "success"
    assert response.report.risk_level == "medium"
    assert [job["status"] for job in repository.jobs] == ["running", "success"]
    assert repository.reports[0]["domain"] == "example.com"


def test_assessment_orchestrator_surfaces_missing_default_model():
    with pytest.raises(HTTPException) as exc:
        AssessmentOrchestrator(FakeRepository(), EmptyModelConfigService(), FakeGateway()).assess_domain(
            "example.com",
            AssessmentRequest(from_date=date(2026, 5, 13), to_date=date(2026, 6, 12)),
        )

    assert exc.value.detail == "No default model configured"


def test_assessment_orchestrator_records_failure_for_model_parse_error():
    repository = FakeRepository()
    with pytest.raises(HTTPException):
        AssessmentOrchestrator(repository, FakeModelConfigService(), NonJsonGateway()).assess_domain(
            "example.com",
            AssessmentRequest(from_date=date(2026, 5, 13), to_date=date(2026, 6, 12)),
        )

    assert [job["status"] for job in repository.jobs] == ["running", "failed"]
