"""
backend/api/routes/data_status.py
------------------------------------
GET  /api/v1/data-status
POST /api/v1/data-status/set-mode   (dev-mode only)
SIH 2026 · PS 26059

Exposes the active data mode, source availability, and per-source
credential/network status.

This endpoint is what the frontend Data Provenance panel and
Forecast Explorer use to show the Judge / evaluator:
  - What data is actually being used
  - Which sources are live vs fixture
  - How to enable research-data mode
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/data-status", tags=["data-status"])
logger = logging.getLogger(__name__)


class SetModeRequest(BaseModel):
    mode: str   # "SYNTHETIC_DEMO" | "RESEARCH_DATA"


@router.get(
    "",
    summary="Current data mode and source availability",
    description=(
        "Returns the active data mode (SYNTHETIC_DEMO | RESEARCH_DATA), "
        "credential/network status for each environmental data source, "
        "and the fallback availability. "
        "SIH 2026 · PS 26059 · Research data requires environment variables."
    ),
)
async def get_data_status():
    """
    Return comprehensive data availability status.
    Safe to call without authentication.
    Never exposes actual credential values.
    """
    import sys
    from pathlib import Path
    _ROOT = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(_ROOT))

    try:
        from data_pipeline.data_mode import get_full_data_status
        status = get_full_data_status()
        return status
    except Exception as exc:
        logger.exception("Data status check failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"error": str(exc), "status": "SERVER_ERROR"},
        ) from exc
