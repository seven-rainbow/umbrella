# Architecture Design

## Purpose

Umbrella Domain Activity stores daily Cisco Umbrella top-1m snapshots and provides a dashboard for inspecting domain ranking history.

The current product answers three questions:

- For a domain, what was its rank on each day in a selected date range?
- What is the current dataset coverage and latest imported snapshot?
- Which domains are currently ranked highest in the latest imported snapshot?

## System Topology

```text
Browser
  |
  | HTTP :80
  v
Frontend container: nginx + built Vue app
  |
  | /api/* reverse proxy
  v
Backend container: FastAPI on :8002
  |
  | clickhouse-connect HTTP protocol
  v
ClickHouse container: MergeTree tables

Ingest worker container
  |
  | downloads Cisco Umbrella zip snapshots
  v
Host-mounted download cache + ClickHouse
```

Runtime services are defined in `docker-compose.yml`:

- `clickhouse`: ClickHouse 24.8 with host-mounted database storage at `${DATA_ROOT}/clickhouse`.
- `backend`: FastAPI app, exposed as `${BACKEND_PORT:-8002}:8002`.
- `ingest-worker`: one-shot backend image command for importing snapshots.
- `frontend`: nginx serving the built Vue application, exposed as `${FRONTEND_PORT:-80}:80`.

The frontend nginx config proxies `/api/` to `http://backend:8002/api/`, so browser code can call relative API URLs.

## Backend Architecture

The backend is a small FastAPI application organized by API routers, service classes, Pydantic models, and a ClickHouse repository.

```text
backend/app/
  main.py              FastAPI app, CORS, router registration
  api/
    health.py          GET /health
    domains.py         GET /api/v1/domains/{domain}/activity
    stats.py           GET /api/v1/stats/overview
                       GET /api/v1/stats/current-top-domains
  services/
    activity.py        domain validation, range validation, activity series summary
    stats.py           dataset overview and latest top domains
    ingest.py          download, validate, parse, and load snapshots
  db/
    clickhouse.py      repository protocol, ClickHouse client, schema, queries, inserts
  cli/
    init_db.py         schema initialization command
    ingest.py          single-date or date-range import command
  core/
    config.py          environment-backed settings
```

`ActivityService` normalizes domains, validates the requested date range, fills missing dates with `null` ranks, and computes summary values such as days seen, coverage ratio, best rank, worst rank, and average rank.

`StatsService` reads dataset-wide metadata and the latest top-ranked domains from ClickHouse.

`IngestService` initializes schema, downloads a snapshot zip, validates zip integrity, deletes any existing rows for the target date, streams CSV rows into ClickHouse in batches, and records import status in `ingest_jobs`.

## API Surface

### Health

```http
GET /health
```

Returns:

```json
{"status": "ok"}
```

### Domain Activity

```http
GET /api/v1/domains/{domain}/activity?from=YYYY-MM-DD&to=YYYY-MM-DD
```

Behavior:

- Domain is trimmed, lowercased, and trailing dots are removed.
- Invalid domain syntax returns HTTP 422.
- `from` must be earlier than or equal to `to`.
- Date range is limited by `MAX_QUERY_DAYS`, currently defaulting to 365.
- Missing dates are returned as points with `rank: null` and `active_score: null`.

Response shape:

```json
{
  "domain": "example.com",
  "from": "2026-01-01",
  "to": "2026-06-10",
  "summary": {
    "days_seen": 120,
    "total_days": 161,
    "coverage_ratio": 0.745,
    "best_rank": 1234,
    "worst_rank": 456789,
    "avg_rank": 98234.56
  },
  "series": [
    {"date": "2026-01-01", "rank": 1234, "active_score": 0.998767}
  ]
}
```

`active_score` is derived from the top-1m rank:

```text
1 - ((rank - 1) / 1_000_000)
```

### Dataset Overview

```http
GET /api/v1/stats/overview
```

Returns minimum snapshot date, maximum snapshot date, number of imported snapshot days, total rank rows, and latest import timestamp.

### Current Top Domains

```http
GET /api/v1/stats/current-top-domains
```

Returns the top 100 domains from the latest imported `snapshot_date`, ordered by ascending rank.

## Storage

The primary table is `domain_rank_daily`:

```sql
CREATE TABLE domain_rank_daily (
    snapshot_date Date,
    domain String,
    rank UInt32,
    imported_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(snapshot_date)
ORDER BY (domain, snapshot_date)
SETTINGS index_granularity = 8192;
```

The sort key is optimized for the main lookup:

```sql
WHERE domain = ?
  AND snapshot_date BETWEEN ? AND ?
```

This is intentionally not sorted by `(snapshot_date, rank)`, because the dominant user workflow is domain history lookup. The latest top-domain query scans one day and orders by rank, which is acceptable for the current dashboard scale.

Import status is tracked in `ingest_jobs`:

```sql
CREATE TABLE ingest_jobs (
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
ORDER BY snapshot_date;
```

Current code appends job records for `running`, `success`, and `failed` states. It does not update previous job rows in place.

## Ingest Flow

The import CLI supports one date or an inclusive date range:

```bash
python -m app.cli.ingest --date 2026-06-08
python -m app.cli.ingest --from 2026-06-01 --to 2026-06-08
```

For each date:

1. Ensure the database schema exists.
2. Resolve the source URL:
   - today: `top-1m.csv.zip`
   - historical date: `top-1m-YYYY-MM-DD.csv.zip`
3. Reuse a cached zip from `DOWNLOAD_CACHE_DIR` when present and valid.
4. Download with explicit headers, connect/read timeouts, random 1-3 second delay, retries, and exponential backoff.
5. Validate the zip and find a CSV member.
6. Delete existing rows for the target `snapshot_date` with a synchronous ClickHouse mutation.
7. Insert `(snapshot_date, domain, rank)` rows in batches.
8. Fail the import if fewer than 900,000 rows were loaded.
9. Append an `ingest_jobs` record for success or failure.

The default Docker worker imports yesterday:

```yaml
command: ["python", "-m", "app.cli.ingest", "--date", "yesterday"]
```

## Frontend Architecture

The frontend is a Vue 3 + Vite single-page dashboard. Production builds are served by nginx.

```text
frontend/src/
  App.vue                         dashboard composition and state
  services/
    activityApi.js                domain activity API client
    statsApi.js                   stats API client
  components/
    OverviewSidebar.vue           dataset and selected-domain metrics
    TopDomainsPanel.vue           latest top 100 list
    QueryPanel.vue                domain and date range controls
    RankChart.vue                 ECharts rank curve
    DailyRankTable.vue            tabular rank detail for selected range
    MetricCard.vue                shared metric display
  styles/main.css                 dashboard styling
```

The dashboard initializes to `example.com` and a 180-day date range ending at the browser's current date. It loads dataset overview and latest top domains on mount. Domain activity is fetched when the user submits the query or selects a domain from the latest top-domain list.

The chart uses reversed rank semantics so better ranks appear higher. Missing rank days remain null and are shown as gaps instead of fabricated values.

## Configuration

Settings are read from environment variables with `.env` support:

| Setting | Default | Purpose |
| --- | --- | --- |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse host |
| `CLICKHOUSE_PORT` | `8123` | ClickHouse HTTP port |
| `CLICKHOUSE_USER` | `default` | ClickHouse user |
| `CLICKHOUSE_PASSWORD` | empty | ClickHouse password |
| `CLICKHOUSE_DATABASE` | `umbrella` | Database name |
| `UMBRELLA_BASE_URL` | `http://s3-us-west-1.amazonaws.com/umbrella-static` | Snapshot source base URL |
| `DOWNLOAD_CACHE_DIR` | `../data/download-cache` | Local zip cache path |
| `DOWNLOAD_CONNECT_TIMEOUT_SECONDS` | `10` | Download connect timeout |
| `DOWNLOAD_READ_TIMEOUT_SECONDS` | `120` | Download read timeout |
| `DOWNLOAD_RETRY_COUNT` | `3` | Download attempts |
| `DOWNLOAD_BACKOFF_SECONDS` | `5` | Base retry backoff |
| `INGEST_BATCH_SIZE` | `100000` | ClickHouse insert batch size |
| `MAX_QUERY_DAYS` | `365` | API query range limit |

## Deployment Choice

ClickHouse in Docker is a practical first production choice for this project when it is deployed as a single-node service. The deployment uses a host-mounted SSD or NVMe data directory, explicit ClickHouse configuration, a persistent download cache, and health checks.

Avoid anonymous Docker volumes for database data. Move away from single-node Docker when the system needs multi-node high availability, several years of history, or broad analytical workloads beyond domain history lookup.

## Resource Estimate

Six months of daily top-1m snapshots:

- Rows: about 180-186 million.
- Raw CSV: about 4.5-8.5 GB.
- ZIP cache: about 1.5-4 GB.
- ClickHouse compressed table: about 5-15 GB.
- Temporary import and merge headroom: 30-50 GB.

Recommended production host:

- CPU: 8 cores.
- Memory: 32 GB.
- Disk: 200-500 GB NVMe SSD.

Minimum production host:

- CPU: 4 cores.
- Memory: 16 GB.
- Disk: 100 GB SSD.

Keep ClickHouse disk usage below 70%. Treat 80% as high risk and 85% as urgent.

## Operational Notes

- Initialize schema with `python -m app.cli.init_db`.
- Import data through the `ingest-worker` service or by running the backend image command manually.
- Re-importing a date is destructive for that date only: existing rows for the date are deleted before new rows are inserted.
- The ingest cache is shared between backend-derived worker runs through `${DATA_ROOT}/download-cache`.
- Backend tests cover ingest behavior, activity calculations, and stats service behavior.
- The current API allows all CORS origins and only GET methods.
