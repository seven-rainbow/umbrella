from __future__ import annotations

import csv
import random
import time
from datetime import date
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import httpx

from app.core.config import Settings
from app.db.clickhouse import ClickHouseRepository


def normalize_ingest_domain(domain: str) -> str | None:
    normalized = domain.strip().lower().rstrip(".")
    return normalized or None


class IngestService:
    def __init__(self, settings: Settings, repository: ClickHouseRepository):
        self.settings = settings
        self.repository = repository
        self.settings.download_cache_dir.mkdir(parents=True, exist_ok=True)

    def source_url(self, snapshot_date: date) -> str:
        today = date.today()
        if snapshot_date == today:
            return f"{self.settings.umbrella_base_url}/top-1m.csv.zip"
        return f"{self.settings.umbrella_base_url}/top-1m-{snapshot_date.isoformat()}.csv.zip"

    def ingest_date(self, snapshot_date: date) -> int:
        self.repository.init_schema()
        url = self.source_url(snapshot_date)
        print(f"[{snapshot_date}] ingest started: {url}", flush=True)
        self.repository.record_job(snapshot_date, url, "running")
        try:
            zip_path = self.download_snapshot(snapshot_date, url)
            rows_loaded = self.load_zip(snapshot_date, zip_path)
            self.repository.record_job(snapshot_date, url, "success", rows_loaded=rows_loaded)
            print(f"[{snapshot_date}] ingest success: rows_loaded={rows_loaded}", flush=True)
            return rows_loaded
        except Exception as exc:
            self.repository.record_job(snapshot_date, url, "failed", error_message=str(exc))
            print(f"[{snapshot_date}] ingest failed: {exc}", flush=True)
            raise

    def download_snapshot(self, snapshot_date: date, url: str) -> Path:
        target = self.settings.download_cache_dir / f"top-1m-{snapshot_date.isoformat()}.csv.zip"
        if target.exists() and target.stat().st_size > 0:
            print(f"[{snapshot_date}] using cached zip: {target}", flush=True)
            self.validate_zip(target)
            return target

        headers = {
            "User-Agent": "umbrella-activity-ingest/1.0",
            "Accept": "application/zip,application/octet-stream,*/*",
        }
        timeout = httpx.Timeout(
            connect=self.settings.download_connect_timeout_seconds,
            read=self.settings.download_read_timeout_seconds,
            write=30,
            pool=30,
        )
        last_error: Exception | None = None

        for attempt in range(1, self.settings.download_retry_count + 1):
            try:
                print(f"[{snapshot_date}] download attempt {attempt}/{self.settings.download_retry_count}", flush=True)
                time.sleep(random.uniform(1, 3))
                with httpx.stream("GET", url, headers=headers, timeout=timeout, follow_redirects=True) as response:
                    response.raise_for_status()
                    tmp_target = target.with_suffix(".tmp")
                    bytes_downloaded = 0
                    with tmp_target.open("wb") as output:
                        next_progress_bytes = 5 * 1024 * 1024
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            output.write(chunk)
                            bytes_downloaded += len(chunk)
                            if bytes_downloaded >= next_progress_bytes:
                                print(
                                    f"[{snapshot_date}] downloaded {bytes_downloaded // 1024 // 1024} MiB",
                                    flush=True,
                                )
                                next_progress_bytes += 5 * 1024 * 1024
                    tmp_target.replace(target)
                self.validate_zip(target)
                print(f"[{snapshot_date}] download complete: {target.stat().st_size // 1024 // 1024} MiB", flush=True)
                return target
            except Exception as exc:
                last_error = exc
                print(f"[{snapshot_date}] download attempt {attempt} failed: {exc}", flush=True)
                if target.exists():
                    target.unlink()
                if attempt < self.settings.download_retry_count:
                    time.sleep(self.settings.download_backoff_seconds * (3 ** (attempt - 1)))

        raise RuntimeError(f"download failed after {self.settings.download_retry_count} attempts: {last_error}")

    def validate_zip(self, path: Path) -> None:
        try:
            with ZipFile(path) as archive:
                bad_member = archive.testzip()
                if bad_member:
                    raise RuntimeError(f"corrupt zip member: {bad_member}")
                csv_members = [name for name in archive.namelist() if name.endswith(".csv")]
                if not csv_members:
                    raise RuntimeError("zip does not contain a csv file")
        except BadZipFile as exc:
            raise RuntimeError("invalid zip file") from exc

    def load_zip(self, snapshot_date: date, zip_path: Path) -> int:
        print(f"[{snapshot_date}] deleting existing rows", flush=True)
        self.repository.delete_snapshot_date(snapshot_date)
        rows_loaded = 0
        rows_seen = 0
        invalid_rows = 0
        batch: list[tuple[date, str, int]] = []

        with ZipFile(zip_path) as archive:
            csv_name = next(name for name in archive.namelist() if name.endswith(".csv"))
            print(f"[{snapshot_date}] loading csv member: {csv_name}", flush=True)
            with archive.open(csv_name) as raw_file:
                text_rows = (line.decode("utf-8").strip() for line in raw_file)
                reader = csv.reader(text_rows)
                for csv_row in reader:
                    rows_seen += 1
                    if len(csv_row) < 2:
                        invalid_rows += 1
                        continue
                    try:
                        rank = int(csv_row[0])
                    except ValueError as exc:
                        invalid_rows += 1
                        if invalid_rows <= 5:
                            print(f"[{snapshot_date}] skipped invalid row {rows_seen}: {csv_row} ({exc})", flush=True)
                        continue
                    domain = normalize_ingest_domain(csv_row[1])
                    if domain is None:
                        invalid_rows += 1
                        if invalid_rows <= 5:
                            print(f"[{snapshot_date}] skipped empty domain row {rows_seen}: {csv_row}", flush=True)
                        continue
                    batch.append((snapshot_date, domain, rank))
                    if len(batch) >= self.settings.ingest_batch_size:
                        self.repository.insert_rank_rows(batch)
                        rows_loaded += len(batch)
                        print(f"[{snapshot_date}] inserted rows={rows_loaded}", flush=True)
                        batch.clear()

        if batch:
            self.repository.insert_rank_rows(batch)
            rows_loaded += len(batch)
            print(f"[{snapshot_date}] inserted rows={rows_loaded}", flush=True)

        print(f"[{snapshot_date}] rows_seen={rows_seen} rows_loaded={rows_loaded} invalid_rows={invalid_rows}", flush=True)

        if rows_loaded < 900_000:
            raise RuntimeError(
                f"unexpected row count for {snapshot_date}: loaded={rows_loaded}, invalid={invalid_rows}, seen={rows_seen}"
            )
        return rows_loaded
