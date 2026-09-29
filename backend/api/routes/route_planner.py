"""
backend/api/routes/route_planner.py
-------------------------------------
POST /api/v1/routes/generate
SIH 2026 · PS 26059
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ...schemas.requests import GenerateRoutesRequest
from ...schemas.responses import ErrorResponse, GenerateRoutesResponse
from ...services import route_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.post(
    "/generate",
    response_model=GenerateRoutesResponse,
    summary="Generate candidate routes",
    description=(
        "Accepts a voyage scenario and runs the deterministic HimDrishti pipeline "
        "(iceberg drift ensemble → POLARIS risk → multi-objective route search). "
        "Returns three candidate routes. "
        "PROTOTYPE: scientific pipeline uses synthetic fixture data. "
        "Not an operational navigation recommendation."
    ),
    responses={
        200: {"description": "Three candidate routes generated successfully"},
        422: {"description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Pipeline execution error"},
    },
)
async def generate_routes(request: GenerateRoutesRequest) -> GenerateRoutesResponse:
    try:
        result = route_service.generate_routes(request)
        logger.info(
            "Routes generated: request_id=%s routes=%d warnings=%d",
            result.request_id,
            len(result.routes),
            len(result.pipeline_warnings),
        )
        return result
    except Exception as exc:
        logger.exception("Route generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline execution failed",
                "detail": "An internal error occurred during route generation. "
                          "No fabricated data will be returned.",
                "status": "SERVER_ERROR",
                "prototype_notice": (
                    "SIH 2026 Prototype — not an operational navigation authority."
                ),
            },
        ) from exc
