"""VitalAI backend entrypoint (FastAPI)."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registers tables)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db import Base, engine
from app import migrate
from app.routers import assistant, auth, blood, diagnosis, emergency, system
from app.services import ml_service

settings = get_settings()
configure_logging(settings.ENVIRONMENT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate.run()  # adds new columns to tables that already exist (e.g. your live Neon DB)
    _ = settings.jwt_secret  # fail fast in production if no secret is configured
    ml_service.registry()  # warm models so the first request is fast
    logger.info("%s ready (llm=%s)", settings.APP_NAME, settings.llm_enabled)
    yield


app = FastAPI(title=f"{settings.APP_NAME} API", version="1.1.0", lifespan=lifespan,
              description="AI-powered health platform: diagnosis, assistant, blood network, emergency.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info("%s %s -> %s (%.0fms)", request.method, request.url.path, response.status_code, (time.time() - start) * 1000)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


for r in (system.router, auth.router, diagnosis.router, assistant.router, blood.router, emergency.router):
    app.include_router(r, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "docs": "/docs", "health": f"{settings.API_PREFIX}/health"}
