from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.pool import close_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    close_pool()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
