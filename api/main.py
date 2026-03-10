from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth_router, assignments_router, billing_router, research_router, webhook_router
from .database import create_all_tables
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://app.scholarassistant.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,        prefix="/api/v1")
app.include_router(assignments_router, prefix="/api/v1")
app.include_router(billing_router,     prefix="/api/v1")
app.include_router(research_router,    prefix="/api/v1")
app.include_router(webhook_router,     prefix="/api/v1")

@app.on_event("startup")
async def startup():
    create_all_tables()
    logger.info("ASA v2 API started")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ASA v2 API"}
