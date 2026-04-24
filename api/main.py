from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import logging

from api.routes.assets import router as assets_router
from api.routes.distribute import router as distribute_router
from api.routes.detect import router as detect_router
from api.routes.dmca import router as dmca_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sportsmark-api")

app = FastAPI(
    title="SportsMark API",
    description="Forensic video watermarking and piracy detection system",
    version="1.0.0"
)

# Enable CORS for React frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up SportsMark API...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down SportsMark API...")

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "SportsMark API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

app.include_router(assets_router, prefix="/assets", tags=["Assets"])
app.include_router(distribute_router, prefix="/distribute", tags=["Distribute"])
app.include_router(detect_router, prefix="/detect", tags=["Detect"])
app.include_router(dmca_router, prefix="/dmca", tags=["DMCA"])
