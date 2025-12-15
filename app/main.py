from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging

from app.database import init_db, get_db
from app.routers import lsp, admin
from app.schemas import HealthCheckResponse
from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="LSP Conflict Detection API",
    description="""
    # LSP (Lease Service Provider) Conflict Detection System

    ## Overview

    This API helps lenders detect conflicts when multiple lenders are working with the same property or customer.

    ## How It Works

    ### 1. Submit Contract
    When a lender submits a contract via `POST /lsp/contracts`:
    - System normalizes address, phone, and email
    - Checks for conflicts with other lenders' contracts (last 90 days)
    - Matches on: APN, Address+ZIP, Email, or Phone
    - Saves contract (even if conflicts exist)
    - Notifies other lenders via webhook if conflicts found
    - Returns conflict information to submitting lender

    ### 2. Update Status
    When a lender updates contract status via `PUT /lsp/contracts/{id}`:
    - Validates ownership (can only update own contracts)
    - Updates status to FUNDED or CANCELLED
    - Resolves all open conflicts
    - Notifies other lenders in conflicts via webhook

    ### 3. Webhook Events
    Other lenders receive notifications when:
    - **NEW_CONFLICT**: Your contract conflicts with a new submission
    - **CONFLICT_RESOLVED**: Conflicting contract was cancelled
    - **CONFLICT_CONTRACT_FUNDED**: Conflicting contract was funded (you lost)

    ## Authentication

    All endpoints require authentication via API key in the `X-API-Key` header.

    ## Webhook Delivery

    Webhooks are signed with HMAC-SHA256 using your API key.
    Verify signature from `X-LSP-Signature` header.

    ## Address Normalization

    Addresses are normalized for consistent matching:
    - Uppercase
    - Standard abbreviations (Street→ST, Avenue→AVE, etc.)
    - Remove punctuation
    - Standardize unit numbers (#100 → UNIT 100)

    Example: "123 Main Street, Apt. 4" → "123 MAIN ST APT 4"
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint to verify API and database connectivity.
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        timestamp=datetime.utcnow(),
        database=db_status
    )


# Include routers
app.include_router(lsp.router)
app.include_router(admin.router)


@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "LSP Conflict Detection API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "submit_contract": "POST /lsp/contracts",
            "update_contract": "PUT /lsp/contracts/{id}",
            "create_lender": "POST /admin/lenders",
            "list_lenders": "GET /admin/lenders"
        }
    }
