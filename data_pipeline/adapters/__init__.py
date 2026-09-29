"""
data_pipeline/adapters/__init__.py
------------------------------------
Adapter package for HimDrishti data pipeline.
SIH 2026 · PS 26059

Each adapter provides a consistent interface for one data source type.
All adapters follow the contract:
  - Return typed schemas (SeaIceField, WindField, etc.)
  - Carry DataProvenance records
  - Never return silently fabricated data
  - Fall back to fixture/replay if live source is unavailable
"""
