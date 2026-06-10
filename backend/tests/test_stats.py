from datetime import date, datetime

from app.services.stats import StatsService


class FakeRepository:
    def fetch_dataset_overview(self):
        return date(2025, 12, 15), date(2026, 6, 8), 186, 186_000_000, datetime(2026, 6, 9, 10, 30)

    def fetch_current_top_domains(self, limit=100):
        return date(2026, 6, 8), [(1, "google.com"), (2, "youtube.com")]


class EmptyRepository:
    def fetch_dataset_overview(self):
        return None, None, 0, 0, None

    def fetch_current_top_domains(self, limit=100):
        return None, []


def test_dataset_overview_maps_repository_values():
    response = StatsService(FakeRepository()).get_dataset_overview()

    assert response.min_date == date(2025, 12, 15)
    assert response.max_date == date(2026, 6, 8)
    assert response.snapshot_days == 186
    assert response.total_rows == 186_000_000
    assert response.latest_imported_at == datetime(2026, 6, 9, 10, 30)


def test_dataset_overview_handles_empty_table():
    response = StatsService(EmptyRepository()).get_dataset_overview()

    assert response.min_date is None
    assert response.max_date is None
    assert response.snapshot_days == 0
    assert response.total_rows == 0
    assert response.latest_imported_at is None


def test_current_top_domains_maps_latest_snapshot_rows():
    response = StatsService(FakeRepository()).get_current_top_domains()

    assert response.snapshot_date == date(2026, 6, 8)
    assert response.domains[0].rank == 1
    assert response.domains[0].domain == "google.com"


def test_current_top_domains_handles_empty_table():
    response = StatsService(EmptyRepository()).get_current_top_domains()

    assert response.snapshot_date is None
    assert response.domains == []
