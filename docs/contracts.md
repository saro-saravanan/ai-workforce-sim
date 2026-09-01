# Contracts v0.2 — data inputs, results, API

These are the interfaces the simulation core, the API, and the web app agree on. The spec (`docs/model-spec.md`) says what is computed; this says how it is laid out.

## 1. Canonical input tables (`data/processed/`)

All CSV, UTF-8, header row. Every table has a sibling `data/provenance/<table>.json` (§4). Rows tagged `FIXTURE` in a `source_tag` column or in provenance are placeholders that the ingestion scripts replace on a machine with network access.

| Table | Key | Columns |
|---|---|---|
| `occupations.csv` | `occ_code` (SOC 2018 6-digit, `11-1011`) | `title`, `major_group` (2-digit), `cluster_id`, `cluster_title`, `emp_national` (heads), `wage_mean_annual`, `wage_p10_annual`, `wage_median_annual`, `baseline_growth_10y` (fraction, from BLS EP), `source_tag` |
| `tasks.csv` | `task_id` | `occ_code`, `task_text`, `weight` (sums to 1 within occ), `exposure_label` (E0/E1/E2), `beta` (Eloundou β in [0,1]), `modality` (software / other_cognitive / interpersonal / physical), `presence` ([0,1]), `use_case` (high_risk / transparency / unregulated), `consequence_high` (0/1), `source_tag` |
| `sectors.csv` | `sector_code` | `title`, `labor_cost_share`, `demand_elasticity`, `tradable` (0/1), `friction` (φ_s), `consumption_share`, `source_tag` |
| `occ_sector.csv` | (`occ_code`, `sector_code`) | `emp_share` (share of the occupation's employment in that sector; sums to 1 per occ), `source_tag` |
| `states.csv` | `fips` (2-digit string) | `name`, `abbrev`, `emp_total`, `source_tag` |
| `occ_state.csv` | (`occ_code`, `fips`) | `emp` (heads), `source_tag` |
| `series/btos.csv` | `period_end` (date) | `share_using_ai`, `wording` (original / business_functions), `weighting` (firm / employment), `source_tag` |
| `series/metr_horizons.csv` | `model` | `date`, `horizon_minutes_p50`, `ci_low_minutes`, `ci_high_minutes`, `source_tag` |
| `series/capex.csv` | (`company`, `year`) | `capex_bn_usd`, `basis` (fiscal / calendar / guidance), `source_tag` |
| `series/regulatory_events.csv` | `event_id` | `region`, `date`, `kind`, `description`, `source_tag` |
| `params/registry.yaml` | `P.xx` | `name`, `central`, `min`, `max`, `unit`, `tag` (S/D/E), `source`, optional `by` (dict for indexed values) |

Phase 1 sector fixture: a single sector `ALL` with `emp_share = 1` for every occupation, `labor_cost_share = 0.58`, `demand_elasticity = 0.8`, `friction = 1`. Replaced by the OEWS industry-occupation matrix on ingest.

Phase 1 state fixture: `occ_state.emp = emp_national × state_share`, with `state_share` from `states.csv` and the same occupational mix in every state. Replaced by OEWS state files on ingest. The map shows a "fixture" badge while this is in force.

## 2. Results document (one per scenario hash)

JSON. Every time-indexed value is an array aligned to `meta.quarters`. Every stochastic series is an object of percentiles; Phase 1 emits `p50` only, and the UI must render a band whenever `p10`/`p90` are present.

```json
{
  "meta": {
    "spec_version": "0.2", "schema_version": "0.2",
    "scenario_id": "baseline", "scenario_hash": "sha256:…", "seed": 42,
    "run_at": "2026-09-01T00:00:00Z", "draws": 1, "ensemble": "central",
    "quarters": ["2024Q1", "…", "2040Q4"],
    "regions": ["US"], "baseline": "no_frontier_ai_after_2023",
    "data_flags": { "occ_state": "FIXTURE", "occ_sector": "FIXTURE", "aei_anchoring": "unavailable" },
    "capability_units": "doublings of METR 50% task horizon (minutes = 2^index)"
  },
  "series": {
    "US": {
      "gdp_pct_vs_baseline":        { "p50": [ … ] },
      "employment_pct_vs_baseline": { "p50": [ … ] },
      "real_wage_pct_vs_baseline":  { "p50": [ … ] },
      "nominal_wage_pct_vs_baseline": { "p50": [ … ] },
      "wage_share_pp_vs_baseline":  { "p50": [ … ] },
      "tfp_pct_vs_baseline":        { "p50": [ … ] },
      "price_index_pct_vs_baseline": { "p50": [ … ] },
      "displaced_workers_cum":      { "p50": [ … ] },
      "adoption_share":             { "p50": [ … ] },
      "ai_spend_bn":                { "p50": [ … ] },
      "capability_index":           { "p50": [ … ] },
      "capability_horizon_hours":   { "p50": [ … ] }
    }
  },
  "occupations": [
    { "occ_code": "43-3031", "title": "Bookkeeping…", "cluster_id": "c043", "major_group": "43",
      "emp0": 1500000, "wage0": 47000,
      "automatable_share": 0.62, "exposure_beta": 0.71,
      "displacement": { "p50": [ … ] },
      "employment_pct_vs_baseline": { "p50": [ … ] },
      "real_wage_pct_vs_baseline": { "p50": [ … ] } }
  ],
  "states": [
    { "fips": "39", "name": "Ohio",
      "employment_pct_vs_baseline": { "p50": [ … ] },
      "real_wage_pct_vs_baseline": { "p50": [ … ] },
      "displaced_workers_cum": { "p50": [ … ] } }
  ],
  "channels": {
    "employment_pct_vs_baseline": {
      "order": ["automation", "augmentation", "demand_response", "reinstatement", "demand_feedback", "ai_investment"],
      "contributions": { "automation": [ … ], "augmentation": [ … ], "…": [ … ] }
    }
  },
  "explain": { "notes": [ "string, plain English, generated from mechanism trace, no free text from an LLM" ] }
}
```

Sizes at Phase 1: ~120 occupations × 68 quarters × 3 metrics plus 51 states × 68 × 3, under 1 MB uncompressed.

## 3. API (FastAPI, `/api`)

| Method | Path | Body / params | Returns |
|---|---|---|---|
| GET | `/api/health` | — | `{status, spec_version, data_flags}` |
| GET | `/api/scenarios` | — | `[ {id, name, parent, description} ]` from `scenarios/*.json` |
| GET | `/api/scenarios/{id}` | — | canonical (inheritance-resolved) scenario JSON |
| POST | `/api/run` | scenario JSON, or `{ "id": "baseline" }` | `{ scenario_hash, meta }`; runs synchronously if not cached |
| GET | `/api/results/{hash}` | — | full results document |
| GET | `/api/results/{hash}/{section}` | section ∈ series, occupations, states, channels, meta | that section only |
| GET | `/api/geo/us-states` | — | GeoJSON (Natural Earth 110m admin-1, US) |
| GET | `/api/params` | — | parameter registry |

Cache key: `sha256` of the canonical scenario JSON plus spec version and data version. Results cached on disk under `data/cache/<hash>.json` (gitignored).

## 4. Provenance record

`data/provenance/<table>.json`:

```json
{ "table": "tasks", "source": "openai/GPTs-are-GPTs full_labelset.tsv (O*NET task statements, Eloundou et al. labels)",
  "source_url": "https://github.com/openai/GPTs-are-GPTs", "license": "MIT",
  "pulled_at": "2026-09-01", "commit": "…", "sha256": "…",
  "transformations": ["normalize coreweight within occupation", "modality keyword classifier v1 (E)", "presence keyword classifier v1 (E)"],
  "status": "real | FIXTURE | partial", "notes": "" }
```

## 5. CLI

```
aiwsim run  --scenario scenarios/baseline.json [--out results.json] [--seed 42]
aiwsim data build            # rebuild data/processed from data/raw + fixtures
aiwsim data status           # print provenance status per table
aiwsim validate              # accounting identities, quiet-aggregate, preset tests
```

## 6. Web state

URL query carries `scenario`, `q` (quarter index), `view`, `metric`, `state`. Pinia store `useScenario` holds the loaded results; `useScrubber` holds the quarter and playback. Theme follows `prefers-color-scheme` with a manual toggle stored in `localStorage`.
