from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol

import clickhouse_connect

from app.core.config import Settings, get_settings


class RankRepository(Protocol):
    def fetch_domain_ranks(self, domain: str, from_date: date, to_date: date) -> list[tuple[date, int]]:
        ...

    def fetch_dataset_overview(self) -> tuple[date | None, date | None, int, int, object | None]:
        ...

    def fetch_current_top_domains(self, limit: int = 100) -> tuple[date | None, list[tuple[int, str]]]:
        ...


class ClickHouseRepository:
    def __init__(self, client, database: str):
        self.client = client
        self.database = database

    @property
    def rank_table(self) -> str:
        return f"{self.database}.domain_rank_daily"

    @property
    def jobs_table(self) -> str:
        return f"{self.database}.ingest_jobs"

    @classmethod
    def from_settings(cls, settings: Settings) -> "ClickHouseRepository":
        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        )
        return cls(client=client, database=settings.clickhouse_database)

    @classmethod
    def admin_from_settings(cls, settings: Settings) -> "ClickHouseRepository":
        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
        )
        return cls(client=client, database=settings.clickhouse_database)

    def init_schema(self) -> None:
        self.client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.rank_table} (
                snapshot_date Date,
                domain String,
                rank UInt32,
                imported_at DateTime DEFAULT now()
            )
            ENGINE = MergeTree
            PARTITION BY toYYYYMM(snapshot_date)
            ORDER BY (domain, snapshot_date)
            SETTINGS index_granularity = 8192
            """
        )
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.jobs_table} (
                snapshot_date Date,
                source_url String,
                status Enum8('pending' = 1, 'running' = 2, 'success' = 3, 'failed' = 4),
                rows_loaded UInt64,
                error_message String,
                retry_count UInt8,
                started_at Nullable(DateTime),
                finished_at Nullable(DateTime),
                created_at DateTime DEFAULT now()
            )
            ENGINE = MergeTree
            ORDER BY snapshot_date
            """
        )

    def fetch_domain_ranks(self, domain: str, from_date: date, to_date: date) -> list[tuple[date, int]]:
        result = self.client.query(
            f"""
            SELECT snapshot_date, rank
            FROM {self.rank_table}
            WHERE domain = {{domain:String}}
              AND snapshot_date >= {{from_date:Date}}
              AND snapshot_date <= {{to_date:Date}}
            ORDER BY snapshot_date
            """,
            parameters={"domain": domain, "from_date": from_date, "to_date": to_date},
        )
        return [(row[0], row[1]) for row in result.result_rows]

    def fetch_dataset_overview(self) -> tuple[date | None, date | None, int, int, object | None]:
        result = self.client.query(
            f"""
            SELECT
                min(snapshot_date),
                max(snapshot_date),
                uniqExact(snapshot_date),
                count(),
                max(imported_at)
            FROM {self.rank_table}
            """
        )
        row = result.result_rows[0]
        return row[0], row[1], int(row[2]), int(row[3]), row[4]

    def fetch_current_top_domains(self, limit: int = 100) -> tuple[date | None, list[tuple[int, str]]]:
        latest_result = self.client.query(f"SELECT max(snapshot_date) FROM {self.rank_table}")
        latest_date = latest_result.result_rows[0][0]
        if latest_date is None:
            return None, []

        result = self.client.query(
            f"""
            SELECT rank, domain
            FROM {self.rank_table}
            WHERE snapshot_date = {{snapshot_date:Date}}
            ORDER BY rank ASC
            LIMIT {{limit:UInt32}}
            """,
            parameters={"snapshot_date": latest_date, "limit": limit},
        )
        return latest_date, [(int(row[0]), row[1]) for row in result.result_rows]

    def delete_snapshot_date(self, snapshot_date: date) -> None:
        self.client.command(
            f"ALTER TABLE {self.rank_table} DELETE WHERE snapshot_date = {{snapshot_date:Date}} SETTINGS mutations_sync = 1",
            parameters={"snapshot_date": snapshot_date},
        )

    def insert_rank_rows(self, rows: Iterable[tuple[date, str, int]]) -> None:
        batch = list(rows)
        if not batch:
            return
        self.client.insert(self.rank_table, batch, column_names=["snapshot_date", "domain", "rank"])

    def record_job(
        self,
        snapshot_date: date,
        source_url: str,
        status: str,
        rows_loaded: int = 0,
        error_message: str = "",
        retry_count: int = 0,
    ) -> None:
        self.client.insert(
            self.jobs_table,
            [(snapshot_date, source_url, status, rows_loaded, error_message[:1000], retry_count)],
            column_names=["snapshot_date", "source_url", "status", "rows_loaded", "error_message", "retry_count"],
        )


def get_repository() -> ClickHouseRepository:
    return ClickHouseRepository.from_settings(get_settings())
