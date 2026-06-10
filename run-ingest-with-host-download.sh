#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$PROJECT_DIR/.env"
  set +a
fi

FROM_DATE="${1:-2025-12-15}"
TO_DATE="${2:-2026-06-08}"
BASE_URL="${UMBRELLA_BASE_URL:-http://s3-us-west-1.amazonaws.com/umbrella-static}"
DATA_ROOT="${DATA_ROOT:-/data02/umbrella-activity}"
CACHE_DIR="${CACHE_DIR:-$DATA_ROOT/download-cache}"
TODAY="$(date +%F)"
FAILED_FILE="$PROJECT_DIR/ingest-failed-dates.txt"
MIN_ROWS_PER_DAY=900000
MAX_DOWNLOAD_ATTEMPTS=8
DOCKER_COMPOSE="${DOCKER_COMPOSE:-docker compose}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-umbrella}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:?CLICKHOUSE_PASSWORD must be set in .env or the environment}"
CLICKHOUSE_DATABASE="${CLICKHOUSE_DATABASE:-umbrella}"

mkdir -p "$CACHE_DIR"
touch "$FAILED_FILE"

log() {
  echo "[$(date '+%F %T')] $*"
}

rows_for_date() {
  local snapshot_date="$1"
  cd "$PROJECT_DIR"
  $DOCKER_COMPOSE exec -T clickhouse clickhouse-client \
    --user "$CLICKHOUSE_USER" \
    --password "$CLICKHOUSE_PASSWORD" \
    --query "SELECT count() FROM $CLICKHOUSE_DATABASE.domain_rank_daily WHERE snapshot_date = '$snapshot_date'" 2>/dev/null || echo 0
}

download_snapshot() {
  local snapshot_date="$1"
  local url="$2"
  local target="$3"
  local tmp="$4"

  if [ -s "$target" ]; then
    log "[$snapshot_date] cache hit: $(du -h "$target" | awk '{print $1}')"
    return 0
  fi

  for attempt in $(seq 1 "$MAX_DOWNLOAD_ATTEMPTS"); do
    log "[$snapshot_date] host download attempt $attempt/$MAX_DOWNLOAD_ATTEMPTS: $url"
    if [ -s "$tmp" ]; then
      log "[$snapshot_date] resuming partial download: $(du -h "$tmp" | awk '{print $1}')"
      resume_args=(-C -)
    else
      resume_args=()
    fi

    if curl -L --fail --connect-timeout 20 --retry 3 --retry-delay 5 --progress-bar "${resume_args[@]}" -o "$tmp" "$url"; then
      mv "$tmp" "$target"
      log "[$snapshot_date] host download complete: $(du -h "$target" | awk '{print $1}')"
      return 0
    fi

    log "[$snapshot_date] host download attempt failed"
    sleep $((attempt * 10))
  done

  log "[$snapshot_date] host download failed after $MAX_DOWNLOAD_ATTEMPTS attempts"
  return 1
}

current="$FROM_DATE"
end_exclusive="$(date -I -d "$TO_DATE + 1 day")"

while [ "$current" != "$end_exclusive" ]; do
  target="$CACHE_DIR/top-1m-$current.csv.zip"
  tmp="$CACHE_DIR/top-1m-$current.csv.tmp"

  if [ "$current" = "$TODAY" ]; then
    url="$BASE_URL/top-1m.csv.zip"
  else
    url="$BASE_URL/top-1m-$current.csv.zip"
  fi

  existing_rows="$(rows_for_date "$current" | tr -d '[:space:]')"
  if [ "${existing_rows:-0}" -ge "$MIN_ROWS_PER_DAY" ]; then
    log "[$current] skip existing import: rows=$existing_rows"
    current="$(date -I -d "$current + 1 day")"
    continue
  fi

  if ! download_snapshot "$current" "$url" "$target" "$tmp"; then
    echo "$current download_failed" >> "$FAILED_FILE"
    current="$(date -I -d "$current + 1 day")"
    continue
  fi

  log "[$current] container import start"
  cd "$PROJECT_DIR"
  if $DOCKER_COMPOSE run --rm \
    -e no_proxy=clickhouse,backend,frontend,localhost,127.0.0.1 \
    -e NO_PROXY=clickhouse,backend,frontend,localhost,127.0.0.1 \
    ingest-worker python -m app.cli.ingest --date "$current"; then
    log "[$current] container import done"
  else
    log "[$current] container import failed"
    echo "$current import_failed" >> "$FAILED_FILE"
  fi

  current="$(date -I -d "$current + 1 day")"
done

log "range complete: $FROM_DATE to $TO_DATE"
log "failed dates file: $FAILED_FILE"
