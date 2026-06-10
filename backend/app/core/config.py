from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "umbrella"
    umbrella_base_url: str = "http://s3-us-west-1.amazonaws.com/umbrella-static"
    download_cache_dir: Path = Path("../data/download-cache")
    download_connect_timeout_seconds: float = 10
    download_read_timeout_seconds: float = 120
    download_retry_count: int = 3
    download_backoff_seconds: float = 5
    ingest_batch_size: int = 100_000
    max_query_days: int = 365

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
