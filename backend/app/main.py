from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.db.pool import close_pool

settings = get_settings()
setup_logging(log_level=settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    close_pool()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)
app.include_router(api_router)
