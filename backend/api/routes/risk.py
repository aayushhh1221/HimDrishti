"""
backend/api/routes/risk.py
----------------------------
GET /api/v1/risk/{route_id}
SIH 2026 · PS 26059
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path

from ...schemas.responses import ErrorResponse, RiskResponse
from ...services import route_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

_VALID_ROUTE_IDS = {"recommended", "alternative1", "higher-risk"}


@router.get(
    "/{route_id}",
    response_model=RiskResponse,
    summary="Get risk profile for a route",
    description=(
        "Returns the POLARIS RIO risk profile for the given route_id. "
        "PROTOTYPE: RIV table is illustrative — not from IMO MSC.1/Circ.1519. "
        "Do not describe result as 'safe', 'certified', or 'approved'."
    ),
    responses={
        200: {"description": "Risk profile returned"},
        404: {"model": ErrorResponse, "description": "Unknown route_id"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def get_risk(
    route_id: str = Path(
        ...,
        description="Route identifier: recommended | alternative1 | higher-risk",
    ),
) -> RiskResponse:
    if route_id not in _VALID_ROUTE_IDS:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Unknown route_id '{route_id}'",
                "detail": f"Valid route IDs: {sorted(_VALID_ROUTE_IDS)}",
                "status": "INVALID_INPUT",
                "prototype_notice": "SIH 2026 Prototype.",
            },
        )
    try:
        return route_service.get_risk(route_id)
    except Exception as exc:
        logger.exception("Risk lookup failed for route_id=%s: %s", route_id, exc)
        raise HTTPException(status_code=500, detail={"status": "SERVER_ERROR"}) from exc
