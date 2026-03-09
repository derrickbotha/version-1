
import json
import logging
import logging.config
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# JSON structured logging
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_object: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_object["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_object)


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(
        logging.DEBUG if settings.environment == "development" else logging.INFO
    )
    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.environment == "development" else logging.WARNING
    )


_configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter (shared instance referenced by routers)
# ---------------------------------------------------------------------------

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # ---- startup ----
    if settings.environment == "development":
        logger.info("Startup: creating database tables (development mode)")
        from app.database.base import Base  # noqa: PLC0415
        from app.database.session import engine  # noqa: PLC0415

        # Import all models so their metadata is registered with Base before
        # create_all is called.
        import app.models.audit_log  # noqa: F401, PLC0415
        import app.models.bid  # noqa: F401, PLC0415
        import app.models.contract  # noqa: F401, PLC0415
        import app.models.job  # noqa: F401, PLC0415
        import app.models.message  # noqa: F401, PLC0415
        import app.models.payment  # noqa: F401, PLC0415  — includes LedgerAccount, LedgerEntry, PaymentMethod, WriterPayout, IdempotencyKey
        import app.models.professor  # noqa: F401, PLC0415  — Institution, ProfessorProfile, ResearcherCredential, ProfessorEndorsement, CourseAssignment, QualityReview, DisputeRuling, ReviewQueueItem, PlatformConfig
        import app.models.submission  # noqa: F401, PLC0415
        import app.models.user  # noqa: F401, PLC0415

        Base.metadata.create_all(bind=engine)
        logger.info("Startup: database tables ready")

    logger.info(
        "Research Marketplace API started",
        # extra fields will be captured by the JSON formatter via getMessage
    )
    yield
    # ---- shutdown ----
    logger.info("Research Marketplace API shutting down")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="Research Marketplace API",
        description=(
            "A marketplace platform connecting students who need research assistance "
            "with qualified researchers."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # Middleware                                                           #
    # ------------------------------------------------------------------ #

    # Rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # Exception handlers                                                  #
    # ------------------------------------------------------------------ #

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"status": "error", "message": "Rate limit exceeded. Slow down."},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        logger.debug("HTTP %s: %s %s", exc.status_code, request.method, request.url)
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "message": exc.detail or "An error occurred"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # Build a human-readable summary of every validation error
        errors: list[str] = []
        for error in exc.errors():
            loc = " -> ".join(str(part) for part in error.get("loc", []))
            msg = error.get("msg", "validation error")
            errors.append(f"{loc}: {msg}" if loc else msg)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Request validation failed",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception for %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "An unexpected error occurred"},
        )

    # ------------------------------------------------------------------ #
    # Routers                                                             #
    # ------------------------------------------------------------------ #

    from app.routers.account_router import router as account_router  # noqa: PLC0415
    from app.routers.admin_router import router as admin_router  # noqa: PLC0415
    from app.routers.admin_router_v2 import router as admin_router_v2  # noqa: PLC0415
    from app.routers.auth_router import router as auth_router  # noqa: PLC0415
    from app.routers.bids_router import router as bids_router  # noqa: PLC0415
    from app.routers.contracts_router import router as contracts_router  # noqa: PLC0415
    from app.routers.disputes_router import router as disputes_router  # noqa: PLC0415
    from app.routers.jobs_router import router as jobs_router  # noqa: PLC0415
    from app.routers.messages_router import router as messages_router  # noqa: PLC0415
    from app.routers.payments_router import router as payments_router  # noqa: PLC0415
    from app.routers.professor_router import router as professor_router  # noqa: PLC0415
    from app.routers.ratings_router import router as ratings_router  # noqa: PLC0415
    from app.routers.submissions_router import router as submissions_router  # noqa: PLC0415
    from app.routers.webhook_router import router as webhook_router  # noqa: PLC0415
    from app.routers.whatsapp_router import router as whatsapp_router  # noqa: PLC0415

    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(account_router, prefix=api_prefix)
    app.include_router(jobs_router, prefix=api_prefix)
    app.include_router(bids_router, prefix=api_prefix)
    app.include_router(contracts_router, prefix=api_prefix)
    app.include_router(messages_router, prefix=api_prefix)
    app.include_router(payments_router, prefix=api_prefix)
    app.include_router(submissions_router, prefix=api_prefix)
    app.include_router(ratings_router, prefix=api_prefix)
    app.include_router(disputes_router, prefix=api_prefix)
    app.include_router(admin_router, prefix=api_prefix)   # original (kept for backwards compat)
    app.include_router(admin_router_v2, prefix=api_prefix)  # enhanced admin endpoints
    app.include_router(professor_router, prefix=api_prefix)
    app.include_router(webhook_router, prefix=api_prefix)
    app.include_router(whatsapp_router, prefix=api_prefix)

    # ------------------------------------------------------------------ #
    # Health check                                                        #
    # ------------------------------------------------------------------ #

    @app.get(
        "/health",
        tags=["Health"],
        summary="Service health check",
        response_model=dict,
    )
    async def health_check() -> dict:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
