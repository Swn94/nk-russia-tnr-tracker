"""FastAPI application for NK-Russia TNR Tracker."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.core.utils.config import get_settings
from packages.core.utils.db import get_db, close_db
from packages.api.routes import actors, cases, candidates, brief

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await get_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
    NK-Russia Human Rights Chain of Command Tracker API

    This API provides access to human rights violation cases, actors (perpetrators/victims),
    evidence documentation, and sanctions candidates related to North Korea and Russia.

    ## Features
    - Track human rights violation cases
    - Document chain of command relationships
    - Generate briefing documents
    - Manage sanctions candidates

    ## Data Sources
    - data.go.kr (통일부 북한이탈주민 API)
    - HUDOC (European Court of Human Rights)
    - Freedom House Transnational Repression Reports
    - UN OHCHR, ICC, OSCE
    """,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(actors.router, prefix="/actors", tags=["Actors"])
app.include_router(cases.router, prefix="/cases", tags=["Cases"])
app.include_router(candidates.router, prefix="/candidates", tags=["Sanctions Candidates"])
app.include_router(brief.router, prefix="/brief", tags=["Briefing"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "operational",
        "endpoints": {
            "actors": "/actors",
            "cases": "/cases",
            "candidates": "/candidates",
            "brief": "/brief",
            "docs": "/docs",
            "health": "/health",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = await get_db()
        await db.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": settings.api_version,
    }
