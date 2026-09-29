"""
data_pipeline/__init__.py
--------------------------
HimDrishti Phase 6 — Real/Public Data Pipeline Foundation
SIH 2026 · PS 26059

Public API for the data_pipeline package.

Architecture:
    adapters/      — source-specific readers (sea ice, ocean, wind, iceberg)
    schemas.py     — typed data contracts (dataclasses + enums)
    validation.py  — pre-processing validation rules
    normalization.py — unit/coordinate/missing-value normalization
    provenance.py  — data lineage tracking
    cache/         — local deterministic file cache
    replay/        — reproducible historical fixture replay
"""

__version__ = "0.1.0"
__phase__ = "Phase 6 — Data Pipeline Foundation"
