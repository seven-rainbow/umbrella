from app.core.config import Settings
from app.db.clickhouse import ClickHouseRepository


def main() -> None:
    repository = ClickHouseRepository.admin_from_settings(Settings())
    repository.init_schema()
    print("ClickHouse schema initialized")


if __name__ == "__main__":
    main()
