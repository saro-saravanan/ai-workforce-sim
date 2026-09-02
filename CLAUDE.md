# ai-workforce-sim — working notes for contributors and agents

Interactive, multi-region simulation of how AI reshapes the workforce and economy (2024–2040).
Model specification: `docs/model-spec.md` (v0.2). Contracts between packages: `docs/contracts.md`.

## Layout
- `sim/aiwsim/` simulation core (Python 3.12, numpy/polars, pure functions, deterministic). Modules follow the spec layers:
  `mc.py` (the batched engine: §2–§6 with a leading draw axis and a region axis; regions read the shared task layer at their access lag), `clock.py` (§3 helpers), `sampling.py` (§7.1 copula draws, §7.2 ensemble cells, tornado draws), `engine.py` (central view + channel decomposition), `pipeline.py` (one scenario end to end, paired compare), `results2.py` (contract §2/§8 document), `calibrate.py` (§7.4), `params.py` (registry + levers), `scenario.py` (§8.1), `regions.py` (regional inputs, wage tiers, consistency guard), `labor.py` (channel switches), `data/` (ingestion and fixtures).
- `api/aiwsim_api/` FastAPI service (contract §3). `web/` Vue 3 + TypeScript + Pinia + D3 (no React).
- `data/processed/` committed canonical tables with `data/provenance/*.json`; `data/raw/` and `data/cache/` are gitignored.
- `scenarios/` versioned JSON scenarios and `schema.json`.

## Commands
- `make setup` (uv + pnpm install), `make data` (`aiwsim data build`), `make run` (baseline → `data/cache/baseline.json`), `make test`, `make lint`, `make demo` (API :8000 + web :5173).
- `uv run aiwsim run --scenario scenarios/<id>.json`, `uv run aiwsim calibrate`, `uv run aiwsim data status`.

## Rules that matter
- Every parameter lives in `data/processed/params/registry.yaml` with a provenance tag (S/D/E). No magic numbers in code without a comment naming the tag and source; `params.py` `_CODE_DEFAULTS` is the only other place, and each entry says why.
- Every dataset has a provenance record; fixtures are labelled FIXTURE and surfaced in `meta.data_flags`.
- Outputs are always relative to the frozen-AI baseline; stochastic series carry p10/p25/p50/p75/p90 plus `central` (draw 0, the scenario as specified). Draws are re-centred on the scenario's lever values.
- Spec §16 records every place the implementation sharpens or departs from the spec text. Update it when you change an equation.
- The chat layer (Phase 4) never computes; it calls the API.
- Do not use React. Do not add a general-equilibrium solver without a spec change.
