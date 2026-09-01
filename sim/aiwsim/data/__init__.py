"""Data layer: builds the canonical input tables in ``data/processed/`` (contracts §1).

Public entry points (wired to ``aiwsim data build`` / ``aiwsim data status`` by the CLI)::

    from aiwsim.data.build import build_all, status

Sub-modules: ``sources`` (source registry), ``provenance`` (per-table JSON records), ``classify``
(keyword-rule task classifiers, E), ``clusters`` (spec §1.1 occupation clusters), ``fixtures``,
``series``, ``registry`` (spec §10 parameters), ``geo``, and ``ingest`` (network scripts).
"""
