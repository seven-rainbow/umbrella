# Umbrella Domain Activity

FastAPI + Vue + ClickHouse 服务，用于导入 Cisco Umbrella top-1m 每日域名排名快照，并查询域名历史排名、数据集概览和最新 Top 100 域名。

## 服务组成

- `clickhouse`: 存储每日排名数据，主表为 `umbrella.domain_rank_daily`。
- `backend`: FastAPI API 服务，容器内监听 `8002`。
- `ingest-worker`: 数据下载和导入任务，复用 backend 镜像。
- `frontend`: nginx 静态站点，反向代理 `/api/` 到 backend。

默认端口：

```text
Frontend:   http://localhost/
Backend:    http://localhost:8002/health
ClickHouse: http://localhost:8123
```

## 目录约定

生产部署默认使用宿主机目录：

```text
${DATA_ROOT}/clickhouse       ClickHouse 数据目录
${DATA_ROOT}/download-cache   Umbrella zip 下载缓存
```

部署前创建目录：

```bash
sudo mkdir -p /data02/umbrella-activity/clickhouse
sudo mkdir -p /data02/umbrella-activity/download-cache
```

## 安装部署

1. 准备环境变量：

```bash
cp .env.example .env
```

按需修改 `.env`，至少建议修改：

```env
CLICKHOUSE_PASSWORD=replace_with_a_strong_password
DATA_ROOT=/data02/umbrella-activity
BACKEND_PORT=8002
FRONTEND_PORT=80
CLICKHOUSE_HTTP_PORT=8123
CLICKHOUSE_NATIVE_PORT=9000
```

下面示例默认使用 Docker Compose v2 的 `docker compose` 命令。如果服务器只安装了独立命令 `docker-compose`，把示例中的 `docker compose` 替换为 `docker-compose` 即可。

2. 构建前端静态文件：

```bash
cd frontend
npm install
npm run build
cd ..
```

3. 构建并启动服务：

```bash
docker compose build
docker compose up -d clickhouse
docker compose up -d backend frontend
```

4. 初始化 ClickHouse 表结构：

```bash
docker compose exec backend python -m app.cli.init_db
```

5. 检查服务：

```bash
docker compose ps
curl http://localhost:8002/health
curl http://localhost/api/v1/stats/overview
```

## 常用服务命令

启动全部服务：

```bash
docker compose up -d
```

停止服务：

```bash
docker compose down
```

重启单个服务：

```bash
docker compose restart backend
docker compose restart frontend
docker compose restart clickhouse
```

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f clickhouse
```

重新构建并更新后端：

```bash
docker compose build backend
docker compose up -d backend
```

重新构建并更新前端：

```bash
cd frontend
npm install
npm run build
cd ..
docker compose build frontend
docker compose up -d frontend
```

## 数据下载和导入

导入单日数据：

```bash
docker compose run --rm ingest-worker python -m app.cli.ingest --date 2026-06-08
```

导入昨天数据：

```bash
docker compose run --rm ingest-worker python -m app.cli.ingest --date yesterday
```

导入日期范围，包含起止日期：

```bash
docker compose run --rm ingest-worker python -m app.cli.ingest --from 2026-06-01 --to 2026-06-08
```

导入逻辑：

- 快照文件下载到 `/data02/umbrella-activity/download-cache`。
- 已存在且有效的 zip 会直接复用。
- 每次导入某一天前，会先删除该 `snapshot_date` 的旧数据。
- 单日导入少于 `900000` 行会判定失败。
- 导入状态会追加写入 `umbrella.ingest_jobs`。

如果容器内下载不稳定，可使用宿主机下载脚本：

```bash
bash run-ingest-with-host-download.sh 2026-06-01 2026-06-08
```

该脚本会先在宿主机下载 zip，再调用 `ingest-worker` 导入，并把失败日期写入：

```text
./ingest-failed-dates.txt
```

脚本会自动读取项目目录下的 `.env`。也可以通过环境变量覆盖 `PROJECT_DIR`、`DATA_ROOT`、`CACHE_DIR`、`DOCKER_COMPOSE`、`CLICKHOUSE_USER`、`CLICKHOUSE_PASSWORD` 和 `CLICKHOUSE_DATABASE`。

脚本会自动选择可用的 Compose 命令：优先使用环境变量 `DOCKER_COMPOSE`，其次使用 `docker-compose`，最后使用 `docker compose`。如果需要显式指定，可这样运行：

```bash
DOCKER_COMPOSE=docker-compose bash run-ingest-with-host-download.sh 2026-06-01 2026-06-08
```

## 定时导入

每天导入昨天快照：

```cron
30 2 * * * cd /opt/umbrella-activity && docker compose run --rm ingest-worker python -m app.cli.ingest --date yesterday >> /var/log/umbrella-ingest.log 2>&1
```

如果使用宿主机下载脚本：

```cron
30 2 * * * cd /opt/umbrella-activity && bash run-ingest-with-host-download.sh $(date -I -d yesterday) $(date -I -d yesterday) >> /var/log/umbrella-ingest.log 2>&1
```

## 运维检查命令

执行下面的 ClickHouse 查询前，先在项目目录加载 `.env`：

```bash
set -a
. ./.env
set +a
```

进入 ClickHouse：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD"
```

如果没有把环境变量加载到当前 shell，可直接从 `.env` 查看密码后传入。

查看数据总览：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT
  min(snapshot_date) AS min_date,
  max(snapshot_date) AS max_date,
  uniqExact(snapshot_date) AS snapshot_days,
  count() AS total_rows,
  max(imported_at) AS latest_imported_at
FROM umbrella.domain_rank_daily
"
```

查看每天导入行数：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT snapshot_date, count() AS rows
FROM umbrella.domain_rank_daily
GROUP BY snapshot_date
ORDER BY snapshot_date DESC
LIMIT 30
"
```

检查某一天是否导入完整：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT count()
FROM umbrella.domain_rank_daily
WHERE snapshot_date = '2026-06-08'
"
```

查看导入任务记录：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT snapshot_date, status, rows_loaded, error_message, created_at
FROM umbrella.ingest_jobs
ORDER BY created_at DESC
LIMIT 50
"
```

查看最近失败导入：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT snapshot_date, error_message, created_at
FROM umbrella.ingest_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 50
"
```

检查 ClickHouse 磁盘占用：

```bash
df -h /data02/umbrella-activity
du -sh /data02/umbrella-activity/clickhouse
du -sh /data02/umbrella-activity/download-cache
```

## 常见维护操作

重新初始化表结构，不会删除已有表：

```bash
docker compose exec backend python -m app.cli.init_db
```

重导某一天：

```bash
docker compose run --rm ingest-worker python -m app.cli.ingest --date 2026-06-08
```

手工删除某一天数据：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
ALTER TABLE umbrella.domain_rank_daily
DELETE WHERE snapshot_date = '2026-06-08'
SETTINGS mutations_sync = 1
"
```

清理下载缓存，保留最近 30 天：

```bash
find /data02/umbrella-activity/download-cache -name 'top-1m-*.csv.zip' -mtime +30 -delete
```

查看 ClickHouse 后台 mutation：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT database, table, mutation_id, command, is_done, latest_fail_reason
FROM system.mutations
WHERE database = 'umbrella'
ORDER BY create_time DESC
LIMIT 20
"
```

查看 ClickHouse 表大小：

```bash
docker compose exec clickhouse clickhouse-client --user umbrella --password "$CLICKHOUSE_PASSWORD" --query "
SELECT
  table,
  formatReadableSize(sum(bytes_on_disk)) AS size,
  sum(rows) AS rows
FROM system.parts
WHERE database = 'umbrella' AND active
GROUP BY table
ORDER BY sum(bytes_on_disk) DESC
"
```

## 备份建议

最低要求：

- 定期备份 `/data02/umbrella-activity/clickhouse`。
- 定期备份 `.env` 和 `deploy/clickhouse/*.xml`。
- 下载缓存可以不备份，但保留缓存能减少重导时的外网下载压力。

停止服务后做冷备：

```bash
docker compose down
tar -czf umbrella-clickhouse-$(date +%F).tar.gz /data02/umbrella-activity/clickhouse
docker compose up -d
```

对于生产环境，更推荐使用存储层快照或 ClickHouse 原生备份方案。

## API

健康检查：

```bash
curl http://localhost:8002/health
```

查询数据集概览：

```bash
curl http://localhost/api/v1/stats/overview
```

查询最新 Top 100：

```bash
curl http://localhost/api/v1/stats/current-top-domains
```

查询域名历史排名：

```bash
curl "http://localhost/api/v1/domains/example.com/activity?from=2026-01-01&to=2026-06-08"
```

## 本地开发

后端：

```bash
cd backend
uv sync --extra dev
uv run pytest
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

运行后端测试：

```bash
cd backend
uv run pytest
```
