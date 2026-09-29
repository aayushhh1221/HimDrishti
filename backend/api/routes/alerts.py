"""
backend/api/routes/alerts.py
------------------------------
GET /api/v1/alerts
SIH 2026 · PS 26059
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ...schemas.responses import AlertsListResponse, ErrorResponse
from ...services import route_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get(
    "",
    response_model=AlertsListResponse,
    summary="Get operational alerts",
    description=(
        "Returns structured alert objects derived from the current pipeline state. "
        "PROTOTYPE: alerts are derived from synthetic fixture data, not real operational "
        "threat assessment. data_mode is always exposed."
    ),
    responses={
        200: {"description": "Alert list returned"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def get_alerts() -> AlertsListResponse:
    try:
        return route_service.get_alerts()
    except Exception as exc:
        logger.exception("Alerts service failed: %s", exc)
        raise HTTPException(status_code=500, detail={"status": "SERVER_ERROR"}) from exc
