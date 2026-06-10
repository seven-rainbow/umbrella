from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from app.core.config import Settings
from app.db.clickhouse import ClickHouseRepository
from app.services.ingest import IngestService


def parse_date(value: str) -> date:
    if value == "yesterday":
        return date.today() - timedelta(days=1)
    return datetime.strptime(value, "%Y-%m-%d").date()


def iter_dates(from_date: date, to_date: date):
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Umbrella top-1m snapshots.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Import one date, YYYY-MM-DD or yesterday.")
    group.add_argument("--from", dest="from_date", help="Import range start, YYYY-MM-DD.")
    parser.add_argument("--to", dest="to_date", help="Import range end, YYYY-MM-DD.")
    args = parser.parse_args()

    settings = Settings()
    repository = ClickHouseRepository.admin_from_settings(settings)
    service = IngestService(settings=settings, repository=repository)

    if args.date:
        service.ingest_date(parse_date(args.date))
        return

    if not args.to_date:
        parser.error("--to is required when --from is used")

    for snapshot_date in iter_dates(parse_date(args.from_date), parse_date(args.to_date)):
        service.ingest_date(snapshot_date)


if __name__ == "__main__":
    main()
