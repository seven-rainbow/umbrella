# Umbrella Domain Activity

Umbrella Domain Activity is a FastAPI + Vue + ClickHouse dashboard for importing Cisco Umbrella top-1m daily domain ranking snapshots and querying historical domain activity.

## Features

- Import daily Cisco Umbrella top-1m ranking snapshots.
- Query a domain's rank trend across a selected date range.
- Show dataset coverage, latest imported snapshot, and total rows.
- Display the latest Top 100 domains.
- Visualize daily rank changes with an ECharts line chart.

## Tech Stack

- Backend: FastAPI, Pydantic, clickhouse-connect
- Frontend: Vue 3, Vite, ECharts
- Storage: ClickHouse MergeTree
- Deployment: Docker Compose

## Project Structure

```text
backend/              FastAPI API, ingest CLI, ClickHouse repository
frontend/             Vue dashboard and nginx production image
deploy/clickhouse/    ClickHouse config
docs/                 Architecture and local deployment notes
docker-compose.yml    Single-node Docker Compose deployment
```

## Documentation

- [Local deployment and operations](docs/local-deployment.md)
- [Architecture](docs/architecture.md)

## License

No license has been specified yet.
