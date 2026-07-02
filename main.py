from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router
from db.database import Base, engine
import logging

logger = logging.getLogger(__name__)

try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:
    logger.warning("Database init skipped at startup: %s", exc)

app = FastAPI(
    title="Lumina Clip API",
    description="Multi-language AI video clipping platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://opsclip.com", "https://www.opsclip.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"app": "Lumina Clip API", "version": "1.0.0", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}
