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

---

# Phase 2 additions (contracts v0.3)

## 7. Cohort input tables (`data/processed/cohorts/`)

| Table | Key | Columns |
|---|---|---|
| `occ_age.csv` | (`occ_code`, `age_band`) | `share` (sums to 1 per occ); bands `16-24`, `25-44`, `45-54`, `55+`; `source_tag` |
| `occ_education.csv` | (`occ_code`, `education`) | `share`; levels `lt_hs`, `hs`, `some_college`, `ba_plus`; `source_tag` |
| `occ_decile.csv` | (`occ_code`, `decile`) | `share`; national individual-earnings decile `1`..`10`; `source_tag` |
| `national_deciles.csv` | `decile` | `lower_bound_annual` (cutpoint), `source_tag` |

Phase 2 build: deciles derived from OEWS percentiles per occupation (lognormal fit through p10/p25/p50/p75/p90) against national cutpoints from the OEWS all-occupations row (D); education derived from O*NET Job Zone through a documented mapping (E); age is a FIXTURE (national CPS age distribution tilted by Job Zone) until the IPUMS CPS ASEC ingest (`ingest/cps_asec.py`) fits the joint distribution. Joint per-occupation cohort weights are the product of marginals (independence within occupation) until then; `meta.data_flags.cohorts` says which.

## 8. Results document additions

- `meta.draws` (int), `meta.ensemble` (`"all"` | `"central"`), `meta.cells` (list of 8 mechanism-cell ids such as `"bessen|acemoglu_low|passthrough_low"`), `meta.percentiles` (`[10,25,50,75,90]`).
- Every stochastic series carries `p10`, `p25`, `p50`, `p75`, `p90` and `central` (the central-parameter run). Phase 1 consumers that read `p50` keep working.
- `structural`: for each headline metric (`employment_pct_vs_baseline`, `gdp_pct_vs_baseline`, `real_wage_pct_vs_baseline`, `wage_share_pp_vs_baseline`): `{ "by_cell": { cell_id: { "p50": [...] } }, "spread": { "2030Q4": { "parametric_pp": x, "structural_pp": y }, "2040Q4": {...} } }` where parametric = mean within-cell p90−p10 and structural = range of cell medians.
- `confidence`: for each headline metric at `2030Q4` and `2040Q4`: `{ "level": "high"|"medium"|"low", "sign_share": 0.0–1.0, "cells_agree": bool, "flip_params": ["P.61", ...] }` per spec §7.3.
- `tornado`: for each headline metric at `2040Q4`: top 15 `{ "param", "name", "tag", "low", "high", "effect_at_low", "effect_at_high" }` from one-at-a-time min/max runs at central for everything else.
- `cohorts`: `{ "age": [ { "band", "employment_pct_vs_baseline": {percentiles}, "share_of_jobs_lost": {percentiles} } ], "education": [...], "income_decile": [...] }` (cumulative to each quarter, arrays aligned to `meta.quarters`).
- `flows`: `{ "origins": [ { "major_group", "title", "jobs_lost_cum": {percentiles} } ], "destinations": { "reemployed": {percentiles}, "retraining": {percentiles}, "unemployed": {percentiles}, "exited": {percentiles}, "retired": {percentiles}, "unfilled_entry": {percentiles} } }` cumulative, for the Sankey.
- `explain.trace`: for each headline metric, central-run intermediate quantities at `2030Q4` and `2040Q4` (`automatable_share`, `realized_D`, `realized_U`, `adoption_emp`, `dln_unit_cost`, `q_ratio`, `mu`, `nu`, `price_index`) as numbers.
- `explain.diff`: canonical diff vs parent (`[{path, from, to, mechanism}]`).

## 9. API additions

| Method | Path | Body / params | Returns |
|---|---|---|---|
| POST | `/api/run` | scenario JSON or `{id}`; optional `"draws"` (1–400) and `"ensemble"` override | `{scenario_hash, meta}`; 200 draws must complete in under 10 s |
| GET | `/api/compare?a=HASH&b=HASH` | two result hashes | `{ "diff": [...], "delta": { "series": { metric: {p10,p50,p90} }, "states": [ {fips, employment_pct_vs_baseline: {p50}} ], "occupations": [ {occ_code, displacement: {p50}} ] }, "confidence": {metric: {...}} }`; deltas are **paired** across draws (same seed) so bands are meaningful |
| GET | `/api/sensitivity/{hash}` | — | the `tornado` section |
| GET | `/api/explain/{hash}?metric=M&quarter=Q` | — | `{ "value": {percentiles at Q}, "channels": {contributions at Q}, "trace": {...}, "confidence": {...}, "top_params": [...] , "notes": [...] }` |
| GET | `/api/levers` | — | lever metadata for the what-if form: `[ { "path": "levers.capability.doubling_months", "label", "group", "type": "number"|"enum"|"boolean", "min", "max", "step", "default", "unit", "param": "P.01", "mechanism": "..." } ]` |
| POST | `/api/scenarios` | scenario JSON with `parent` | saves to `scenarios/user/<id>.json` (gitignored), returns the canonical scenario |
| GET | `/api/scenarios` | — | now includes `"preset": true` for the report-replication presets and `"user": true` for saved ones |

## 10. Web state additions

`compare=HASH_B` in the URL selects the comparison scenario; `cell=` selects a mechanism cell in the dashboard's structural view; `cohort=age|education|income` selects the cohort facet.
