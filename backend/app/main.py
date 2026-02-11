from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import async_session, engine
from app.core.init_db import create_tables, seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    async with async_session() as db:
        await seed_all(db)
    yield
    await engine.dispose()


app = FastAPI(
    title="Clinic Schedule API",
    version="0.1.0",
    description="多層条件・自然文対応 職員シフト作成システム",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
