from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Protocol

import clickhouse_connect

from app.core.config import Settings, get_settings


class RankRepository(Protocol):
    def fetch_domain_ranks(self, domain: str, from_date: date, to_date: date) -> list[tuple[date, int]]:
        ...

    def fetch_dataset_overview(self) -> tuple[date | None, date | None, int, int, object | None]:
        ...

    def fetch_current_top_domains(self, limit: int = 100) -> tuple[date | None, list[tuple[int, str]]]:
        ...

    def fetch_latest_snapshot_date(self) -> date | None:
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

    @property
    def volatility_table(self) -> str:
        return f"{self.database}.domain_volatility_daily"

    @property
    def assessment_jobs_table(self) -> str:
        return f"{self.database}.domain_assessment_jobs"

    @property
    def assessment_reports_table(self) -> str:
        return f"{self.database}.domain_assessment_reports"

    @property
    def providers_table(self) -> str:
        return f"{self.database}.llm_providers"

    @property
    def models_table(self) -> str:
        return f"{self.database}.llm_model_configs"

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
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.volatility_table} (
                snapshot_date Date,
                domain String,
                latest_rank UInt32,
                rank_delta_1d Nullable(Int32),
                rank_delta_7d Nullable(Int32),
                rank_delta_30d Nullable(Int32),
                percentile_shift Float64,
                is_new_entry Bool,
                is_disappeared Bool,
                volatility_score Float64,
                reason String,
                created_at DateTime DEFAULT now()
            )
            ENGINE = ReplacingMergeTree(created_at)
            PARTITION BY toYYYYMM(snapshot_date)
            ORDER BY (snapshot_date, domain)
            """
        )
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.assessment_jobs_table} (
                job_id String,
                domain String,
                status Enum8('pending' = 1, 'running' = 2, 'success' = 3, 'failed' = 4),
                error_message String,
                model_id String,
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            )
            ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY (job_id, updated_at)
            """
        )
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.assessment_reports_table} (
                job_id String,
                domain String,
                risk_level String,
                confidence Float64,
                summary String,
                key_findings String,
                recommended_actions String,
                evidence String,
                model_provider String,
                model_name String,
                report_json String,
                created_at DateTime DEFAULT now()
            )
            ENGINE = ReplacingMergeTree(created_at)
            ORDER BY (domain, created_at, job_id)
            """
        )
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.providers_table} (
                provider_id String,
                name String,
                provider_type String,
                base_url String,
                api_key_secret_ref String,
                enabled Bool,
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            )
            ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY provider_id
            """
        )
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.models_table} (
                model_id String,
                provider_id String,
                model_name String,
                temperature Float64,
                max_tokens UInt32,
                timeout_seconds Float64,
                is_default Bool,
                created_at DateTime DEFAULT now(),
                updated_at DateTime DEFAULT now()
            )
            ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY model_id
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
        latest_date = self.fetch_latest_snapshot_date()
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

    def fetch_latest_snapshot_date(self) -> date | None:
        latest_result = self.client.query(f"SELECT max(snapshot_date) FROM {self.rank_table}")
        return latest_result.result_rows[0][0]

    def fetch_volatile_domains(self, snapshot_date: date | None, limit: int = 100) -> tuple[date | None, list[dict[str, Any]]]:
        target_date = snapshot_date or self.fetch_latest_snapshot_date()
        if target_date is None:
            return None, []
        result = self.client.query(
            f"""
            WITH
                latest AS (
                    SELECT domain, rank AS latest_rank
                    FROM {self.rank_table}
                    WHERE snapshot_date = {{snapshot_date:Date}}
                ),
                d1 AS (
                    SELECT domain, rank
                    FROM {self.rank_table}
                    WHERE snapshot_date = subtractDays({{snapshot_date:Date}}, 1)
                ),
                d7 AS (
                    SELECT domain, rank
                    FROM {self.rank_table}
                    WHERE snapshot_date = subtractDays({{snapshot_date:Date}}, 7)
                ),
                d30 AS (
                    SELECT domain, rank
                    FROM {self.rank_table}
                    WHERE snapshot_date = subtractDays({{snapshot_date:Date}}, 30)
                )
            SELECT
                latest.domain,
                latest.latest_rank,
                if(isNull(d1.rank), NULL, latest.latest_rank - d1.rank) AS rank_delta_1d,
                if(isNull(d7.rank), NULL, latest.latest_rank - d7.rank) AS rank_delta_7d,
                if(isNull(d30.rank), NULL, latest.latest_rank - d30.rank) AS rank_delta_30d,
                if(isNull(d30.rank), 1, abs(latest.latest_rank - d30.rank) / 1000000) AS percentile_shift,
                isNull(d30.rank) AS is_new_entry,
                false AS is_disappeared,
                least(1, greatest(
                    if(isNull(d7.rank), 0, abs(latest.latest_rank - d7.rank) / 100000),
                    if(isNull(d30.rank), 0.8, abs(latest.latest_rank - d30.rank) / 300000),
                    if(latest.latest_rank <= 100000 AND isNull(d7.rank), 0.9, 0)
                )) AS volatility_score,
                multiIf(
                    latest.latest_rank <= 100000 AND isNull(d7.rank), 'new top-100k entry',
                    isNull(d30.rank), 'new top-1m entry within 30 days',
                    isNotNull(d7.rank) AND latest.latest_rank - d7.rank <= -10000, '7-day rank surge',
                    isNotNull(d7.rank) AND latest.latest_rank - d7.rank >= 10000, '7-day rank drop',
                    'rank volatility'
                ) AS reason
            FROM latest
            LEFT JOIN d1 USING domain
            LEFT JOIN d7 USING domain
            LEFT JOIN d30 USING domain
            WHERE abs(ifNull(latest.latest_rank - d7.rank, 0)) >= 10000
               OR (latest.latest_rank <= 100000 AND isNull(d7.rank))
               OR isNull(d30.rank)
            ORDER BY volatility_score DESC, latest.latest_rank ASC
            LIMIT {{limit:UInt32}}
            """,
            parameters={"snapshot_date": target_date, "limit": limit},
        )
        rows = []
        for row in result.result_rows:
            rows.append(
                {
                    "domain": row[0],
                    "latest_rank": int(row[1]),
                    "rank_delta_1d": row[2],
                    "rank_delta_7d": row[3],
                    "rank_delta_30d": row[4],
                    "percentile_shift": float(row[5]),
                    "is_new_entry": bool(row[6]),
                    "is_disappeared": bool(row[7]),
                    "volatility_score": float(row[8]),
                    "reason": row[9],
                }
            )
        return target_date, rows

    def insert_provider(self, provider: dict[str, Any]) -> None:
        self.client.insert(
            self.providers_table,
            [
                (
                    provider["provider_id"],
                    provider["name"],
                    provider["provider_type"],
                    provider["base_url"],
                    provider["api_key_secret_ref"],
                    provider["enabled"],
                    datetime.utcnow(),
                )
            ],
            column_names=["provider_id", "name", "provider_type", "base_url", "api_key_secret_ref", "enabled", "updated_at"],
        )

    def insert_model_config(self, model: dict[str, Any]) -> None:
        self.client.insert(
            self.models_table,
            [
                (
                    model["model_id"],
                    model["provider_id"],
                    model["model_name"],
                    model["temperature"],
                    model["max_tokens"],
                    model["timeout_seconds"],
                    model["is_default"],
                    datetime.utcnow(),
                )
            ],
            column_names=[
                "model_id",
                "provider_id",
                "model_name",
                "temperature",
                "max_tokens",
                "timeout_seconds",
                "is_default",
                "updated_at",
            ],
        )

    def fetch_providers(self) -> list[dict[str, Any]]:
        result = self.client.query(
            f"""
            SELECT provider_id, name, provider_type, base_url, api_key_secret_ref, enabled
            FROM {self.providers_table}
            FINAL
            ORDER BY name
            """
        )
        return [
            {
                "provider_id": row[0],
                "name": row[1],
                "provider_type": row[2],
                "base_url": row[3],
                "api_key_secret_ref": row[4],
                "enabled": bool(row[5]),
            }
            for row in result.result_rows
        ]

    def fetch_models(self) -> list[dict[str, Any]]:
        result = self.client.query(
            f"""
            SELECT model_id, provider_id, model_name, temperature, max_tokens, timeout_seconds, is_default
            FROM {self.models_table}
            FINAL
            ORDER BY is_default DESC, model_name
            """
        )
        return [
            {
                "model_id": row[0],
                "provider_id": row[1],
                "model_name": row[2],
                "temperature": float(row[3]),
                "max_tokens": int(row[4]),
                "timeout_seconds": float(row[5]),
                "is_default": bool(row[6]),
            }
            for row in result.result_rows
        ]

    def set_default_model(self, model_id: str) -> None:
        models = self.fetch_models()
        for model in models:
            model["is_default"] = model["model_id"] == model_id
            self.insert_model_config(model)

    def get_model_with_provider(self, model_id: str | None = None) -> dict[str, Any] | None:
        models = self.fetch_models()
        target = next((model for model in models if model["model_id"] == model_id), None) if model_id else None
        if target is None:
            target = next((model for model in models if model["is_default"]), None)
        if target is None:
            return None
        providers = {provider["provider_id"]: provider for provider in self.fetch_providers()}
        provider = providers.get(target["provider_id"])
        if provider is None or not provider["enabled"]:
            return None
        return {"model": target, "provider": provider}

    def record_assessment_job(self, job_id: str, domain: str, status: str, model_id: str = "", error_message: str = "") -> None:
        self.client.insert(
            self.assessment_jobs_table,
            [(job_id, domain, status, error_message[:2000], model_id, datetime.utcnow())],
            column_names=["job_id", "domain", "status", "error_message", "model_id", "updated_at"],
        )

    def insert_assessment_report(self, report: dict[str, Any]) -> None:
        self.client.insert(
            self.assessment_reports_table,
            [
                (
                    report["job_id"],
                    report["domain"],
                    report["risk_level"],
                    report["confidence"],
                    report["summary"],
                    report["key_findings"],
                    report["recommended_actions"],
                    report["evidence"],
                    report["model_provider"],
                    report["model_name"],
                    report["report_json"],
                )
            ],
            column_names=[
                "job_id",
                "domain",
                "risk_level",
                "confidence",
                "summary",
                "key_findings",
                "recommended_actions",
                "evidence",
                "model_provider",
                "model_name",
                "report_json",
            ],
        )

    def fetch_assessment_job(self, job_id: str) -> dict[str, Any] | None:
        result = self.client.query(
            f"""
            SELECT job_id, domain, status, error_message, model_id, created_at, updated_at
            FROM {self.assessment_jobs_table}
            FINAL
            WHERE job_id = {{job_id:String}}
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            parameters={"job_id": job_id},
        )
        if not result.result_rows:
            return None
        row = result.result_rows[0]
        return {
            "job_id": row[0],
            "domain": row[1],
            "status": row[2],
            "error_message": row[3],
            "model_id": row[4],
            "created_at": row[5],
            "updated_at": row[6],
        }

    def fetch_assessment_report_by_job(self, job_id: str) -> dict[str, Any] | None:
        result = self.client.query(
            f"""
            SELECT report_json
            FROM {self.assessment_reports_table}
            FINAL
            WHERE job_id = {{job_id:String}}
            ORDER BY created_at DESC
            LIMIT 1
            """,
            parameters={"job_id": job_id},
        )
        return {"report_json": result.result_rows[0][0]} if result.result_rows else None

    def fetch_domain_assessment_reports(self, domain: str, limit: int = 20) -> list[dict[str, Any]]:
        result = self.client.query(
            f"""
            SELECT job_id, report_json, created_at
            FROM {self.assessment_reports_table}
            FINAL
            WHERE domain = {{domain:String}}
            ORDER BY created_at DESC
            LIMIT {{limit:UInt32}}
            """,
            parameters={"domain": domain, "limit": limit},
        )
        return [{"job_id": row[0], "report_json": row[1], "created_at": row[2]} for row in result.result_rows]

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
