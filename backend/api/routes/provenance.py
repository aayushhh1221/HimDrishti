"""
backend/api/routes/provenance.py
----------------------------------
GET /api/v1/provenance
SIH 2026 · PS 26059
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ...schemas.responses import ErrorResponse, ProvenanceResponse
from ...services import route_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/provenance", tags=["provenance"])


@router.get(
    "",
    response_model=ProvenanceResponse,
    summary="Get data provenance records",
    description=(
        "Returns lineage records for all datasets used in the current pipeline run. "
        "Each record includes source, dataset, valid times, spatial coverage, units, "
        "and status. PROTOTYPE: all records are SYNTHETIC_DEMO fixture."
    ),
    responses={
        200: {"description": "Provenance records returned"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def get_provenance() -> ProvenanceResponse:
    try:
        return route_service.get_provenance()
    except Exception as exc:
        logger.exception("Provenance service failed: %s", exc)
        raise HTTPException(status_code=500, detail={"status": "SERVER_ERROR"}) from exc
