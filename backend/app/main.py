import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal, init_db
from app.routers import auth, branding, dictionaries, estimates, health, users
from app.seed import seed

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.validate_production()
    if settings.is_production and settings.seed_demo_data:
        logger.warning(
            "SEED_DEMO_DATA=true в production: демо-учётки с известными паролями "
            "доступны всем. Смените пароли или отключите сид."
        )
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as session:
            seed(session)
    yield


app = FastAPI(
    title="Калькулятор себестоимости и раскроя",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(dictionaries.router, prefix="/api")
app.include_router(branding.router, prefix="/api")
app.include_router(estimates.router, prefix="/api")
app.include_router(estimates.public_router, prefix="/api")
app.include_router(branding.public_router, prefix="/api")
