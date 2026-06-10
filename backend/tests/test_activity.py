from datetime import date

import pytest
from fastapi import HTTPException

from app.services.activity import ActivityService, active_score, normalize_domain


class FakeRepository:
    def fetch_domain_ranks(self, domain: str, from_date: date, to_date: date):
        assert domain == "example.com"
        return [(date(2026, 1, 1), 1), (date(2026, 1, 3), 1_000_000)]


def test_normalize_domain_lowercases_and_removes_trailing_dot():
    assert normalize_domain(" Example.COM. ") == "example.com"


def test_normalize_domain_rejects_invalid_domain():
    with pytest.raises(HTTPException):
        normalize_domain("-bad.example")


def test_active_score_uses_top_1m_rank():
    assert active_score(1) == 1.0
    assert active_score(1_000_000) == 0.000001
    assert active_score(None) is None


def test_activity_service_fills_missing_dates_and_summary():
    response = ActivityService(FakeRepository()).get_activity(
        "example.com",
        date(2026, 1, 1),
        date(2026, 1, 3),
    )

    assert response.summary.days_seen == 2
    assert response.summary.total_days == 3
    assert response.summary.best_rank == 1
    assert response.summary.worst_rank == 1_000_000
    assert response.summary.avg_rank == 500000.5
    assert [point.rank for point in response.series] == [1, None, 1_000_000]

