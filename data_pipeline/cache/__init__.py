"""
data_pipeline/cache/__init__.py
---------------------------------
Local deterministic cache for downloaded/generated datasets.
SIH 2026 · PS 26059

Design principles:
  - Deterministic file naming (source + time window + config hash)
  - Metadata sidecar with provenance + retrieval timestamp
  - No accidental overwrite (explicit force=True required)
  - No credentials stored in cache files or metadata
  - SHA-256 checksum of cached data
  - Simple filesystem layout (no Redis / Postgres / cloud)

Cache directory:
    data/cache/  (relative to project root)
    Set HIMDRISHTI_CACHE_DIR env var to override.

Layout:
    data/cache/
        sea_ice/
            <hash>.npy          ← numpy array
            <hash>.meta.json    ← provenance + checksum
        ocean_current/
            <hash>.npy
            <hash>.meta.json
        wind/
            <hash>.npy
            <hash>.meta.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache root
# ---------------------------------------------------------------------------

def _cache_root() -> Path:
    override = os.environ.get("HIMDRISHTI_CACHE_DIR")
    if override:
        return Path(override)
    # Resolve relative to this file's location: data_pipeline/cache/ -> project root
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "data" / "cache"


def _category_dir(category: str) -> Path:
    d = _cache_root() / category
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def make_cache_key(
    category: str,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    start_time: datetime,
    end_time: datetime,
    extra: str = "",
) -> str:
    """
    Deterministic cache key from spatial/temporal query parameters.
    Returns a short hex string (first 16 chars of SHA-256).
    """
    raw = (
        f"{category}|"
        f"{lat_min:.3f}|{lat_max:.3f}|{lon_min:.3f}|{lon_max:.3f}|"
        f"{start_time.isoformat()}|{end_time.isoformat()}|"
        f"{extra}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

def cache_exists(category: str, key: str) -> bool:
    """True if both the data file and metadata sidecar exist."""
    d = _category_dir(category)
    return (d / f"{key}.npy").exists() and (d / f"{key}.meta.json").exists()


def write_cache(
    category: str,
    key: str,
    data: np.ndarray,
    metadata: Dict[str, Any],
    force: bool = False,
) -> Path:
    """
    Write numpy array + metadata to cache.

    Parameters
    ----------
    category : str  e.g. "sea_ice", "wind"
    key      : str  from make_cache_key()
    data     : np.ndarray
    metadata : dict  must NOT contain credentials
    force    : bool  if False, raises if cache entry already exists

    Returns the path of the written data file.
    """
    d = _category_dir(category)
    data_path = d / f"{key}.npy"
    meta_path = d / f"{key}.meta.json"

    if data_path.exists() and not force:
        raise FileExistsError(
            f"Cache entry {category}/{key} already exists. "
            "Use force=True to overwrite.")

    np.save(str(data_path), data)

    # Compute checksum of saved file
    checksum = _sha256_file(data_path)

    full_meta = {
        **metadata,
        "cached_at": datetime.now(tz=timezone.utc).isoformat(),
        "cache_key": key,
        "category": category,
        "sha256": checksum,
        "array_shape": list(data.shape),
        "array_dtype": str(data.dtype),
    }
    # Safety: scrub any credential-like keys before writing
    for bad_key in ["password", "token", "api_key", "secret", "credential"]:
        full_meta.pop(bad_key, None)

    meta_path.write_text(json.dumps(full_meta, indent=2), encoding="utf-8")
    logger.info("Cache write: %s/%s.npy (%s) sha256=%s",
                category, key, data.shape, checksum[:12])
    return data_path


def read_cache(
    category: str,
    key: str,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Read numpy array + metadata from cache.
    Verifies SHA-256 checksum before returning.

    Returns (data_array, metadata_dict).
    Raises FileNotFoundError if cache miss.
    Raises ValueError if checksum mismatch.
    """
    d = _category_dir(category)
    data_path = d / f"{key}.npy"
    meta_path = d / f"{key}.meta.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Cache miss: {category}/{key}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected_checksum = meta.get("sha256", "")
    actual_checksum = _sha256_file(data_path)

    if expected_checksum and actual_checksum != expected_checksum:
        raise ValueError(
            f"Cache checksum mismatch for {category}/{key}. "
            f"Expected {expected_checksum[:12]}…, got {actual_checksum[:12]}…. "
            "Cache may be corrupted.")

    data = np.load(str(data_path), allow_pickle=False)
    logger.debug("Cache hit: %s/%s shape=%s", category, key, data.shape)
    return data, meta


def invalidate_cache(category: str, key: str) -> None:
    """Remove a specific cache entry (data + metadata)."""
    d = _category_dir(category)
    for suffix in [".npy", ".meta.json"]:
        p = d / f"{key}{suffix}"
        if p.exists():
            p.unlink()
            logger.info("Cache invalidated: %s", p)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_summary() -> Dict[str, int]:
    """Return count of cached files per category."""
    root = _cache_root()
    summary = {}
    if root.exists():
        for cat_dir in root.iterdir():
            if cat_dir.is_dir():
                n = len(list(cat_dir.glob("*.npy")))
                summary[cat_dir.name] = n
    return summary
