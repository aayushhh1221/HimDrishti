"""
backend/api/routes/health.py
SIH 2026 · PS 26059
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    prototype_notice: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns HTTP 200 when the HimDrishti API is running.",
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="HimDrishti API",
        version="0.1.0",
        prototype_notice=(
            "SIH 2026 Prototype · PS 26059 · "
            "Demonstration system only · Not an operational navigation authority."
        ),
    )
