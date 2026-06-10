from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.core.config import Settings
from app.services.ingest import IngestService


class FakeRepository:
    def __init__(self):
        self.deleted_dates = []
        self.rows = []
        self.jobs = []

    def init_schema(self):
        pass

    def record_job(self, *args, **kwargs):
        self.jobs.append((args, kwargs))

    def delete_snapshot_date(self, snapshot_date):
        self.deleted_dates.append(snapshot_date)

    def insert_rank_rows(self, rows):
        self.rows.extend(rows)


def make_service(tmp_path: Path, repository: FakeRepository) -> IngestService:
    settings = Settings(download_cache_dir=tmp_path, ingest_batch_size=2)
    return IngestService(settings=settings, repository=repository)


def test_validate_zip_rejects_missing_csv(tmp_path):
    repository = FakeRepository()
    service = make_service(tmp_path, repository)
    zip_path = tmp_path / "empty.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("readme.txt", "no csv")

    with pytest.raises(RuntimeError, match="csv"):
        service.validate_zip(zip_path)


def test_load_zip_imports_rows_and_deletes_existing_snapshot(tmp_path):
    repository = FakeRepository()
    service = make_service(tmp_path, repository)
    zip_path = tmp_path / "small.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("top-1m.csv", "1,example.com\n2,openai.com\n900000,iana.org\n")

    with pytest.raises(RuntimeError, match="unexpected row count"):
        service.load_zip(date(2026, 1, 1), zip_path)

    assert repository.deleted_dates == [date(2026, 1, 1)]
    assert repository.rows == [
        (date(2026, 1, 1), "example.com", 1),
        (date(2026, 1, 1), "openai.com", 2),
        (date(2026, 1, 1), "iana.org", 900000),
    ]


def test_load_zip_keeps_source_domains_without_strict_format_validation(tmp_path):
    repository = FakeRepository()
    service = make_service(tmp_path, repository)
    zip_path = tmp_path / "invalid.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("top-1m.csv", "1,example.com\n2,-bad.example\n3,openai.com\n")

    with pytest.raises(RuntimeError, match="unexpected row count"):
        service.load_zip(date(2026, 1, 2), zip_path)

    assert repository.rows == [
        (date(2026, 1, 2), "example.com", 1),
        (date(2026, 1, 2), "-bad.example", 2),
        (date(2026, 1, 2), "openai.com", 3),
    ]
