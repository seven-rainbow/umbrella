from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.domains import router as domains_router
from app.api.health import router as health_router
from app.api.stats import router as stats_router

app = FastAPI(title="Umbrella Domain Activity API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(domains_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")
