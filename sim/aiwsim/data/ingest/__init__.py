"""Ingest scripts for machines WITH network access (this sandbox reaches only github.com).

Each script is idempotent, writes its table(s) into ``data/processed/`` and a provenance record, and
supports ``--check`` (verify URLs only) and ``--dry-run`` (report without writing)::

    uv run python -m aiwsim.data.ingest.oews --check
    uv run python -m aiwsim.data.ingest.ep --dry-run
    uv run python -m aiwsim.data.ingest.onet
    uv run python -m aiwsim.data.ingest.btos
    uv run python -m aiwsim.data.ingest.aei
    uv run python -m aiwsim.data.ingest.ilostat        # Phase 3: occ_region (Asia) via ISCO->SOC
    uv run python -m aiwsim.data.ingest.eurostat_lfs   # Phase 3: occ_region (EU-27), lfsa_egai2d
    uv run python -m aiwsim.data.ingest.epoch_models   # Phase 3: actor_releases (+ ECI)
    uv run python -m aiwsim.data.ingest.oecd_tiva      # Phase 3: trade_weights, import_share

Where ``docs/data-inventory.md`` records only a landing page, the file URL used here follows the
publisher's naming convention and is marked ``# NOT IN INVENTORY`` beside its definition.  None of
these scripts has been executed against the live sites; ``--check`` is the first thing to run.
"""
