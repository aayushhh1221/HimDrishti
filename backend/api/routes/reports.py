"""
backend/api/routes/reports.py
-------------------------------
POST /api/v1/reports/export          — Voyage Plan & POLARIS Dossier (PDF)
POST /api/v1/reports/export/environmental — Environmental Exposure Summary (PDF)

PDF generation: Jinja2 + WeasyPrint (server-side).
Falls back to JSON dossier if WeasyPrint native libs (GTK/Pango) are unavailable.

The Indian national flag image is embedded as a base64 data URI so WeasyPrint
can resolve it without filesystem path ambiguity.

Design: matched to Report Reference/himdrishti_gov_report_template_with_flag.html
  - Flag LEFT, immediately beside "Government of India"
  - Ministry of Earth Sciences below
  - NCPOR identity on the right
  - HIMDRISHTI brand strip

No environmental metrics are fabricated.
All values come from the frontend session payload.

SIH 2026 · PS 26059 / PS 26188
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

logger = logging.getLogger("himdrishti.api.reports")

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_FLAG_PATH    = _TEMPLATE_DIR / "assets" / "indian-flag-uploaded.png"

# ---------------------------------------------------------------------------
# Flag: embed as base64 data URI so WeasyPrint resolves it on all platforms
# ---------------------------------------------------------------------------

def _flag_data_uri() -> str:
    """Return the Indian flag as a base64-encoded PNG data URI."""
    try:
        raw = _FLAG_PATH.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except FileNotFoundError:
        logger.warning("Flag asset not found at %s — header will show alt text only", _FLAG_PATH)
        return ""

_FLAG_URI = _flag_data_uri()   # computed once at startup

# ---------------------------------------------------------------------------
# Jinja2 / WeasyPrint — deferred import (GTK/Pango optional)
# ---------------------------------------------------------------------------

_JINJA_AVAILABLE = False
_XHTML2PDF_AVAILABLE = False
_jinja_env = None

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    _jinja_env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    _JINJA_AVAILABLE = True
    logger.info("Jinja2 templates loaded from: %s", _TEMPLATE_DIR)
except ImportError as _e:
    logger.warning("Jinja2 not available: %s", _e)

try:
    from xhtml2pdf import pisa as _pisa_test  # noqa: F401
    _XHTML2PDF_AVAILABLE = True
    logger.info("xhtml2pdf (ReportLab) PDF engine: AVAILABLE")
except ImportError:
    logger.info("xhtml2pdf not installed — WeasyPrint only")


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class AuditEventPayload(BaseModel):
    id: str
    timestamp: str
    role: str
    action: str
    detail: str
    session_id: str = Field(alias="sessionId", default="")

    model_config = {"populate_by_name": True}


class CaptainDecisionPayload(BaseModel):
    state: str
    route_id: str
    route_name: str
    timestamp: str
    remarks: str = ""


class VoyageConfigPayload(BaseModel):
    origin_name: str
    destination_name: str
    departure_time: str
    vessel_name: str
    operating_mode: str
    max_acceptable_risk: float


class RouteSnapshotPayload(BaseModel):
    route_id: str
    name: str
    total_distance_nm: float | None = None
    estimated_duration_hours: float | None = None
    polaris_rio: int | None = None
    risk_level: str | None = None
    data_mode: str
    convergence_note: str | None = None
    is_distinct: bool = True
    prototype_notice: str


class ReportExportRequest(BaseModel):
    session_id: str
    voyage_config: VoyageConfigPayload
    selected_route: RouteSnapshotPayload
    captain_decision: CaptainDecisionPayload | None = None
    audit_events: list[AuditEventPayload] = Field(default_factory=list)
    export_format: str = "pdf"
    sea_ice_forecast: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Dossier builder
# ---------------------------------------------------------------------------

def _build_dossier(request: ReportExportRequest, now_utc: str) -> dict[str, Any]:
    captain = request.captain_decision
    return {
        "dossier_type":      "HIMDRISHTI_VOYAGE_DOSSIER",
        "generated_at_utc":  now_utc,
        "session_id":        request.session_id,
        "sea_ice_forecast":  request.sea_ice_forecast,

        "prototype_disclaimer": (
            "This document is a demonstration output of the HimDrishti SIH 2026 prototype. "
            "It is not an official Government of India publication, not an operational "
            "navigation instruction, and not a substitute for authoritative charts, forecasts, "
            "ice information, vessel procedures, or the professional judgment of the "
            "Captain / Master. POLARIS RIV values are illustrative — not from IMO MSC.1/Circ.1519."
        ),

        "voyage_configuration": {
            "origin":              request.voyage_config.origin_name,
            "destination":         request.voyage_config.destination_name,
            "departure_time":      request.voyage_config.departure_time,
            "vessel":              request.voyage_config.vessel_name,
            "operating_mode":      request.voyage_config.operating_mode,
            "max_acceptable_risk": request.voyage_config.max_acceptable_risk,
        },

        "selected_route": {
            "route_id":                 request.selected_route.route_id,
            "name":                     request.selected_route.name,
            "total_distance_nm":        request.selected_route.total_distance_nm,
            "estimated_duration_hours": request.selected_route.estimated_duration_hours,
            "polaris_rio":              request.selected_route.polaris_rio,
            "risk_level":               request.selected_route.risk_level,
            "data_mode":                request.selected_route.data_mode,
            "is_distinct":              request.selected_route.is_distinct,
            "convergence_note":         request.selected_route.convergence_note,
            "prototype_notice":         request.selected_route.prototype_notice,
        },

        "captain_decision": {
            "state":      captain.state      if captain else "PENDING",
            "route_id":   captain.route_id   if captain else request.selected_route.route_id,
            "route_name": captain.route_name if captain else request.selected_route.name,
            "timestamp":  captain.timestamp  if captain else now_utc,
            "remarks":    captain.remarks    if captain else "",
        },

        "audit_log": [
            {"id": e.id, "timestamp": e.timestamp, "role": e.role,
             "action": e.action, "detail": e.detail}
            for e in request.audit_events
        ],

        "audit_event_count": len(request.audit_events),
    }


# ---------------------------------------------------------------------------
# PDF generation helper
# ---------------------------------------------------------------------------

def _render_pdf(template_name: str, context: dict[str, Any]) -> bytes | None:
    """
    Render template via Jinja2, then convert to PDF.

    Engine priority:
      1. WeasyPrint (if GTK/Pango native libs available) — best quality
      2. xhtml2pdf/ReportLab (pure Python, no system libs) — works on Windows
      3. None  -> caller falls back to JSON

    The xhtml2pdf path uses a separate table-layout template
    (`*_pisa.html`) because xhtml2pdf supports only CSS 2.1
    (no flex / grid).
    """
    if not _JINJA_AVAILABLE or _jinja_env is None:
        return None

    # ── Try WeasyPrint first (best output, needs GTK) ──────────────────
    try:
        from weasyprint import HTML as WP_HTML  # deferred — needs GTK/Pango
        template = _jinja_env.get_template(template_name)
        html_str = template.render(**context)
        pdf_bytes = WP_HTML(string=html_str).write_pdf()
        logger.info("PDF engine: WeasyPrint (%d bytes)", len(pdf_bytes))
        return pdf_bytes
    except (ImportError, OSError) as exc:
        logger.info("WeasyPrint unavailable (%s) — trying xhtml2pdf", exc)
    except Exception as exc:
        logger.exception("WeasyPrint rendering error: %s", exc)
        # fall through to xhtml2pdf

    # ── Try xhtml2pdf / ReportLab (pure Python, Windows-native) ────────
    if _XHTML2PDF_AVAILABLE:
        try:
            from xhtml2pdf import pisa
            import io

            # xhtml2pdf needs a CSS2.1-compatible (table-layout) template
            pisa_template_name = template_name.replace(".html", "_pisa.html")
            # Fall back to same template if no pisa variant exists
            try:
                template = _jinja_env.get_template(pisa_template_name)
            except Exception:
                template = _jinja_env.get_template(template_name)

            html_str = template.render(**context)
            buf = io.BytesIO()

            def _link_cb(uri: str, rel: str) -> str:
                # Images are embedded as data URIs — no filesystem lookup needed
                return uri

            result = pisa.pisaDocument(
                io.BytesIO(html_str.encode("utf-8")),
                buf,
                link_callback=_link_cb,
            )
            if not result.err:
                pdf_bytes = buf.getvalue()
                logger.info("PDF engine: xhtml2pdf/ReportLab (%d bytes)", len(pdf_bytes))
                return pdf_bytes
            else:
                logger.warning("xhtml2pdf rendering error: %s", result.err)
        except Exception as exc:
            logger.exception("xhtml2pdf rendering exception: %s", exc)

    return None


def _pdf_response(pdf_bytes: bytes, filename: str, session_id: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition":     f'attachment; filename="{filename}"',
            "X-HimDrishti-Session":    session_id,
            "X-HimDrishti-PDF-Engine": "WeasyPrint/Jinja2",
        },
    )


def _json_fallback(dossier: dict[str, Any], session_id: str, reason: str) -> JSONResponse:
    dossier["_pdf_fallback_reason"] = reason
    return JSONResponse(
        content=dossier,
        headers={
            "Content-Disposition": (
                f'attachment; filename="himdrishti_dossier_{session_id[:8]}.json"'
            ),
        },
    )


# ---------------------------------------------------------------------------
# POST /api/v1/reports/export — Voyage Plan & POLARIS Dossier
# ---------------------------------------------------------------------------

@router.post(
    "/export",
    summary="Export Voyage Plan & POLARIS Dossier as PDF",
    description=(
        "Generates a government-style A4 PDF dossier via Jinja2 + WeasyPrint. "
        "Header: Indian national flag LEFT beside 'Government of India / Ministry of Earth Sciences', "
        "NCPOR identity right, HIMDRISHTI brand strip. "
        "Falls back to JSON if WeasyPrint GTK/Pango libs are unavailable. "
        "No environmental data is fabricated. "
        "SIH 2026 · PS 26059"
    ),
    responses={
        200: {"description": "PDF (application/pdf) or JSON fallback"},
        500: {"description": "Rendering error"},
    },
)
def export_report(request: ReportExportRequest) -> Response:
    now_utc = datetime.now(timezone.utc).isoformat()
    dossier = _build_dossier(request, now_utc)
    captain = request.captain_decision

    logger.info(
        "Dossier export: session=%s route=%s decision=%s events=%d",
        request.session_id,
        request.selected_route.route_id,
        captain.state if captain else "none",
        len(request.audit_events),
    )

    context = {
        "dossier":          dossier,
        "flag_src":         _FLAG_URI,
        "alerts":           [],    # alerts not part of voyage dossier payload (separate endpoint)
        "provenance":       [],   # same
        "sea_ice_forecast": dossier.get("sea_ice_forecast"),
    }

    pdf = _render_pdf("voyage_dossier.html", context)

    if pdf:
        filename = (
            f"himdrishti_dossier_{request.session_id[:8]}_"
            f"{now_utc[:10].replace('-', '')}.pdf"
        )
        logger.info("PDF generated: session=%s size=%d bytes", request.session_id, len(pdf))
        return _pdf_response(pdf, filename, request.session_id)

    return _json_fallback(
        dossier, request.session_id,
        "WeasyPrint GTK/Pango native libs not available on this deployment. "
        "Download this JSON and print from a browser for a PDF copy.",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/reports/export/environmental — Environmental Exposure Summary
# ---------------------------------------------------------------------------

class EnvironmentalExportRequest(BaseModel):
    session_id: str
    voyage_config: VoyageConfigPayload
    selected_route: RouteSnapshotPayload
    captain_decision: CaptainDecisionPayload | None = None
    audit_events: list[AuditEventPayload] = Field(default_factory=list)
    # Only fields actually available from the pipeline are accepted.
    # Temperature, waves, visibility, pressure are NOT accepted — they are
    # not available and must not be fabricated.
    forecast_horizon_hours: int | None = None
    forecast_horizon_steps: list[int] = Field(default_factory=list)
    forecast_data_mode: str = "SYNTHETIC_DEMO"
    forecast_prototype_notice: str = "HimDrishti SIH 2026 prototype pipeline output."
    sea_ice_steps: list[dict[str, Any]] = Field(default_factory=list)
    iceberg_summary: list[dict[str, Any]] = Field(default_factory=list)
    hazard_summary: list[dict[str, Any]] = Field(default_factory=list)
    provenance_records: list[dict[str, Any]] = Field(default_factory=list)
    alert_records: list[dict[str, Any]] = Field(default_factory=list)
    export_format: str = "pdf"
    sea_ice_forecast: dict[str, Any] | None = None


@router.post(
    "/export/environmental",
    summary="Export Environmental Exposure Summary as PDF",
    description=(
        "Generates a government-style A4 PDF environmental summary via Jinja2 + WeasyPrint. "
        "Only pipeline-available values are included: sea-ice, iceberg ensemble, hazard field, "
        "provenance, alerts. Temperature, waves, visibility, pressure are NOT included. "
        "Falls back to JSON if WeasyPrint GTK/Pango libs are unavailable. "
        "SIH 2026 · PS 26059"
    ),
)
def export_environmental(request: EnvironmentalExportRequest) -> Response:
    now_utc = datetime.now(timezone.utc).isoformat()
    dossier = _build_dossier(
        ReportExportRequest(
            session_id=request.session_id,
            voyage_config=request.voyage_config,
            selected_route=request.selected_route,
            captain_decision=request.captain_decision,
            audit_events=request.audit_events,
            sea_ice_forecast=request.sea_ice_forecast,
        ),
        now_utc,
    )

    forecast_ctx = None
    if request.forecast_horizon_hours is not None:
        forecast_ctx = {
            "horizon_hours":    request.forecast_horizon_hours,
            "horizon_steps":    request.forecast_horizon_steps,
            "data_mode":        request.forecast_data_mode,
            "prototype_notice": request.forecast_prototype_notice,
            "sea_ice_steps":    request.sea_ice_steps,
            "iceberg_summary":  request.iceberg_summary,
            "hazard_summary":   request.hazard_summary,
        }

    provenance = [
        {"name": p.get("name", p.get("dataset_name", "Unknown")),
         "record": p.get("record", p.get("status", "")),
         "retrieved_at": p.get("retrieved_at", "")}
        for p in request.provenance_records
    ]
    alerts = [
        {"type": a.get("type", a.get("severity", "")),
         "message": a.get("message", a.get("title", "")),
         "time": a.get("time", "")}
        for a in request.alert_records
    ]

    logger.info(
        "Environmental export: session=%s forecast=%s provenance=%d alerts=%d",
        request.session_id,
        "yes" if forecast_ctx else "no",
        len(provenance),
        len(alerts),
    )

    context = {
        "dossier":          dossier,
        "flag_src":         _FLAG_URI,
        "forecast":         forecast_ctx,
        "provenance":       provenance,
        "alerts":           alerts,
        "sea_ice_forecast": request.sea_ice_forecast or dossier.get("sea_ice_forecast"),
    }

    pdf = _render_pdf("environmental_exposure.html", context)

    if pdf:
        filename = (
            f"himdrishti_env_summary_{request.session_id[:8]}_"
            f"{now_utc[:10].replace('-', '')}.pdf"
        )
        logger.info("Environmental PDF: session=%s size=%d bytes", request.session_id, len(pdf))
        return _pdf_response(pdf, filename, request.session_id)

    return _json_fallback(
        dossier, request.session_id,
        "WeasyPrint GTK/Pango native libs not available on this deployment.",
    )
