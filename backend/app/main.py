from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal, init_db
from app.routers import auth, dictionaries, estimates, health
from app.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as session:
            seed(session)
    yield


app = FastAPI(title="Калькулятор себестоимости и раскроя", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(dictionaries.router, prefix="/api")
app.include_router(estimates.router, prefix="/api")
app.include_router(estimates.public_router, prefix="/api")
