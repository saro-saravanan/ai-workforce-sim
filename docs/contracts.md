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

`aiwsim data fetch [--force]` downloads the raw inputs listed in `sim/aiwsim/data/fetch.py` (openai/GPTs-are-GPTs at a pinned commit, Natural Earth at a pinned tag), verifying each SHA-256; `aiwsim data build` fetches whatever is missing unless `--no-fetch` is given. `data/raw/` is never committed.

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

`compare=` in the URL selects the comparison scenario by scenario id (preferred, shareable) or by result hash; `cell=` selects a mechanism cell in the dashboard's structural view; `cohort=age|education|income` selects the cohort facet.

---

# Phase 3 additions (contracts v0.4): regions, actors, supply timeline

## 11. Regional input tables (`data/processed/regions/`)

Region ids: `US`, `EU` (EU-27), `UK`, `CN`, `JP`, `KR`, `IN`, `TW`, `SG`, `RoA` (rest of Asia). The U.S. keeps its state split; the EU gets a member split.

| Table | Key | Columns |
|---|---|---|
| `regions.csv` | `region_id` | `name`, `population`, `gdp_bn_usd`, `employment_total`, `wage_level_rel_us` (mean wage relative to U.S.), `emp_growth_10y` (baseline), `import_share` (tradable demand met by imports), `epl_multiplier` (layoff friction multiplier, EU-style protection < 1), `avail_delay_quarters` (δ^reg for closed frontier models), `frontier_lag_quarters` (domestic-actor lag when foreign frontier is unavailable), `compliance_premium_high_risk`, `regime` (`state_patchwork` / `eu_ai_act` / `licensing` / `light`), `data_center_share` (share of global inference capacity located there), `spillover_weight_us` (adoption spillover weight from the U.S.), `source_tag` |
| `region_members.csv` | `iso3` | `region_id`, `name`, `population`, `gdp_bn_usd` (Natural Earth estimates, real), `source_tag`. Every Natural Earth country appears; countries outside the ten regions carry `region_id = ""` and are drawn neutral on the map |
| `occ_region.csv` | (`occ_code`, `region_id`) | `emp` (heads), `wage_mean_annual_usd`, `source_tag`. Phase 3 build: FIXTURE structural proxy: U.S. occupational mix tilted by log GDP per capita (high-skill major groups scale up with income, physical/agricultural groups scale down), scaled to `employment_total`; wages = U.S. occupation wage × `wage_level_rel_us`. Replaced by the ILOSTAT / Eurostat LFS ingest through the SOC↔ISCO crosswalk |
| `trade_weights.csv` | (`region_from`, `region_to`) | `weight` (share of `region_to`'s tradable demand that is met from `region_from`; rows sum to 1 over `region_from` for each `region_to`, including the domestic share), `source_tag` (FIXTURE until OECD TiVA ingest) |
| `actors.csv` | `actor_id` | `name`, `region_id`, `role` (`lab` / `compute` / `chokepoint`), `weights_posture` (`closed` / `open-lagged` / `open-frontier`), `frontier_lag_quarters`, `releases_per_year`, `price_frontier_usd_per_mtok`, `avail_US`, `avail_EU`, `avail_UK`, `avail_CN`, `avail_JP`, `avail_KR`, `avail_IN`, `avail_TW`, `avail_SG`, `avail_RoA` (0–1), `source_tag` |
| `actor_releases.csv` | (`actor_id`, `model`) | `date` (YYYY-MM-DD), `capability_index` (doublings on the METR clock where the model appears in `series/metr_horizons.csv`, else null), `open_weights` (0/1), `note`, `source_tag` (transcribed public release history; replaced by the Epoch Notable Models ingest) |
| `value_chain.csv` | `stage` | `share_of_spend` (model / compute / chips / integration, sums to 1), `allocation` (`market_share` / `data_center` / `fixed` / `domestic`), `fixed_US`, `fixed_TW`, `fixed_EU`, `fixed_KR` (used when allocation = fixed), `source_tag` |

## 12. Results document additions

- `meta.regions` lists the region ids in the run; `series` is keyed by region id and contains the same metrics for every region, plus `ai_rents_received_bn` (rents accruing to the region by value-chain stage, `{"model": s, "compute": s, "chips": s, "integration": s, "total": s}`) and `ai_spend_bn`.
- `regions`: `[ { "region_id", "name", "employment_total", "gdp_bn_usd", "data_flags": {...} } ]`.
- `world`: `[ { "iso3", "name", "region_id", "employment_pct_vs_baseline": {slim}, "real_wage_pct_vs_baseline": {slim} } ]` — one entry per Natural Earth country in a modelled region; members carry their region's series (composition only) until member-level data exists, and `meta.data_flags.members` says so.
- `states` unchanged (U.S.).
- `occupations[].by_region`: `{ region_id: { "displacement": {central}, "employment_pct_vs_baseline": {central} } }` for the non-U.S. regions (central only, document size).
- `supply`: `{ "clock": {percentiles of capability_index}, "horizon_hours": {…}, "regional_capability": { region_id: {"central": [...]}}, "price_frontier_usd_per_mtok": {"central": [...]}, "price_fixed_capability_usd_per_mtok": {"central": [...]}, "releases": [ {actor_id, name, region_id, model, date, quarter, capability_index, open_weights} ], "regulatory_events": [ {event_id, region, date, quarter, kind, description} ], "availability": { region_id: { actor_id: [0/1 per quarter] } }, "market_share": { region_id: { actor_id: {"central": [...]} } } }`.
- `channels` per region for the U.S. only in Phase 3 (runtime); other regions carry `channels` on request in Phase 5.
- `explain.notes` gain region comparisons (which region is hit first, where rents flow).

## 13. API additions

| Method | Path | Returns |
|---|---|---|
| GET | `/api/geo/world` | Natural Earth 110m admin-0 GeoJSON reduced to `{iso3, name, region_id}` |
| GET | `/api/regions` | `regions.csv` rows |
| GET | `/api/actors` | actors and releases |
| POST | `/api/run` | unchanged; `regions` in the body (list of ids) restricts the run, default all |

## 14. Web state additions

`region=` in the URL (`world` default, or a region id) selects the region every view reads; the map drills `World › EU › Germany` and `World › US › Ohio`.

# Phase 4 additions (contracts v0.5): chat, insights, briefs

## 15. Chat layer (`POST /api/chat`)

The chat layer is a thin, stateless agent over the same results documents the UI reads. It never computes numbers: every figure in a reply comes from a tool result, and the reply carries the tool log so the UI can show what grounded it.

**Request**

```json
{
  "messages": [{"role": "user" | "assistant", "content": "text"}],
  "context": {"scenario_hash": "sha256:…", "scenario_id": "baseline", "compare_hash": "sha256:…", "compare_id": "…", "region": "US", "quarter": "2035Q4", "view": "economy"},
  "confirmed_proposals": ["prop-…"],
  "mode": "chat" | "explain" | "insights"
}
```

`messages` is the visible transcript (text only; the last turn must be the user's). `context` is the current UI state and becomes the default for every tool call. `confirmed_proposals` lists proposal ids the user has confirmed; `run_scenario` on any other proposal returns `needs_confirmation` to the model, which must then ask. `mode` adds a hint: `explain` (call `explain` for the context metric and quarter first), `insights` (call `candidate_insights` first, report the top three with mechanism and confidence).

**Response**

```json
{
  "reply": "markdown text",
  "tool_calls": [{"name": "propose_scenario", "input": {...}, "ok": true, "seconds": 0.1, "summary": "2 lever change(s) validated; proposal prop-…"}],
  "proposed_scenario": {"proposal_id": "prop-…", "scenario": {…scenario document…}, "diff": [{"path", "from", "to", "mechanism"}], "parent": "baseline", "rationale": "…"} | null,
  "proposals": [...],
  "runs": [{"scenario_hash": "sha256:…", "scenario_id": "…", "scenario_name": "…"}],
  "usage": {"input_tokens": n, "output_tokens": n},
  "model": "claude-opus-5",
  "stop_reason": "end_turn"
}
```

`proposed_scenario.scenario` is a valid schema-0.2 child scenario the UI can run through `POST /api/run` (the Run button) or edit in the levers drawer; `proposed_scenario.diff` is the annotated diff vs its parent. `GET /api/proposals/{proposal_id}` returns a proposal again. `GET /api/chat/status` → `{available, model, reason}`; `POST /api/chat` returns 503 with the reason when `ANTHROPIC_API_KEY` is not set on the API server, 502 on backend errors.

**Tools available to the model** (strict schemas; all read-only except `propose_scenario`, which validates without running, and `run_scenario`):
`list_scenarios`, `list_levers(group)`, `get_scenario(id)`, `propose_scenario(parent, name, levers, shocks, remove_shocks, rationale)`, `run_scenario(scenario_id | proposal_id, draws)`, `get_summary(hash, region)`, `explain(hash, metric, quarter, region)`, `compare_runs(hash_a, hash_b)`, `sensitivity(hash, metric)`, `top_occupations(hash, quarter, by, n, min_employment)`, `cohorts(hash, quarter)`, `regions(hash, quarter)`, `candidate_insights(hash, region)`.

Model: `claude-opus-5` by default (`AIWSIM_CHAT_MODEL` overrides), adaptive thinking, server-side refusal fallback (`fallbacks: "default"`). The client is injectable (`aiwsim_api.chat.set_client`) so tests run a scripted fake without credentials.

## 16. Insights and briefs

| Method | Path | Returns |
|---|---|---|
| GET | `/api/insights/{hash}?region=US&n=3` | `{scenario_hash, region, top: [insight…], candidates: [insight…], method}` — deterministic, no model call. An insight is `{key, title, statement, mechanism, confidence, surprise (0–1), evidence, metric, quarter, region}`; `candidates` is every candidate sorted by surprise |
| GET | `/api/brief/{hash}?format=md|html|json&region=US&compare=HASH_A` | Shareable brief: headline table with bands and sign confidence at 2030Q4 and 2040Q4, lever diff vs parent, optional paired comparison against `compare`, top-3 findings with mechanism and confidence, model notes, sensitivity table, regional table, method and provenance (data flags, hash for reproduction), scenario JSON appendix. `md` returns `text/markdown`, `html` a self-contained page (light/dark, print), `json` `{scenario_hash, markdown}` |
| POST | `/api/brief/{hash}` | body `{narrative, region, format}`: the same brief with a model-written narrative (the chat reply the user chose to include) appended under a heading that labels it as such |

Insight candidates (`api/aiwsim_api/insights.py`): output up while employment down; displacement through hiring rather than layoffs; the dominant sensitivity parameter and sign flips; structural vs parametric spread; age and decile incidence; the price channel behind real wages; leading occupations; regional rent concentration and divergence; sign confidence; adoption breadth vs labor effect. Each candidate states its mechanism (spec section and parameter) and inherits the run's confidence classification.

## 17. Web state additions

The chat panel is a third mode of the right-hand panel (`Explain · Ask`). It sends the current `scenario_hash`, `compare_hash`, `region`, and `quarter` as context. A proposed scenario renders as a diff card with **Run** (runs through the results store, sets it as the current or compare scenario) and **Edit** (opens the levers drawer pre-filled). `Export brief` on the top bar downloads the Markdown or opens the HTML brief for the current run (with the compare run when one is selected). In mock mode the panel answers with canned replies and the deterministic insights of the mock document.

# Phase 5 additions (contracts v0.6): static demo export

## 18. Static export (`python -m aiwsim_api.export_static --out web/public/static`)

A public demo needs no server: the exporter runs the scenarios once and writes every document the web app would otherwise fetch from the API. The web app in static mode (`VITE_STATIC=1`) reads these files under `${BASE_URL}static/` and disables what needs a live engine (running new scenarios, chat).

| File | Content |
|---|---|
| `manifest.json` | `{generated_at, spec_version, data_version, draws, runs: [{id, name, parent, description, preset, hash, draws, ensemble, file}], compares: [{a, b, file}], levers: "levers.json", regions: "regions.json", actors: "actors.json", geo: {us_states, world}, insights: {"<id>": file, "<id>__vs__<a>": file}, briefs: {"<id>": {md, html}}}` — `a`, `b`, and insight keys are scenario ids |
| `runs/<id>.json` | the results document of `GET /api/results/{hash}` with `occupations[].by_region` removed (document size) and `meta.static = true` |
| `compare/<a>__<b>.json` | `GET /api/compare?a=&b=` for baseline vs every other run |
| `insights/<id>.json`, `insights/<id>__vs__baseline.json` | `GET /api/insights/{hash}?n=10` without and with `compare=` |
| `briefs/<id>.md`, `briefs/<id>.html` | `GET /api/brief/{hash}` in both formats |
| `levers.json`, `regions.json`, `actors.json` | the corresponding API responses |
| `geo/us-states.geojson`, `geo/world.geojson` | the geo endpoints |

Static mode in the client: scenarios from the manifest; `runScenario(id or hash)` from `runs/`; `compareRuns` from `compare/` when present, else the client-side paired difference; `fetchInsights` from `insights/`; brief links to `briefs/`; explain client-side from the document (as in mock mode); `fetchChatStatus` → `{available: false, reason: "static demo"}`; running a new scenario throws a friendly error and the levers drawer says so. The top bar badge reads `static demo · precomputed runs` and links to the repository. `VITE_BASE` sets the Vite `base` for hosting under a path (GitHub Pages: `/ai-workforce-sim/`).

# Phase 6 additions (contracts v0.7): application layer, embodied channels

## 19. Input tables (`data/processed/applications/`)

| Table | Key | Columns | Status |
|---|---|---|---|
| `embodiment_classes.csv` | `cls` ∈ {driving, manip, fixed, aerial} | `a_emb`, `theta_lo`, `theta_hi` (doublings on the class clock), `tau_months`, `saturation`, `unit_price_2025_usd`, `lifetime_years`, `opex_ratio`, `utilization`, `task_units_per_hour`, `g_max_per_year`, `cum_production_2025`, `adjacent_jobs_per_unit`, `stock_2024_<region>`, `prod_share_<region>`, `note`, `source_tag` | FIXTURE (E, V?) |
| `applications.csv` | `app_id` | `name`, `family`, `cls` (semicolon list), `platform` (0/1), `occ_codes` (semicolon list or `*manip`), `regions_first`, `anchor`, `constraints`, `provisional_profitable`, `provisional_deployed50`, `source_tag` | FIXTURE (E) |
| `approval_paths.csv` | (`cls`, `region_id`) | `start_year`, `full_year`, `j0`, `j_full`, `source_tag` | FIXTURE (E, V?) |
| `self_employed.csv` | (`occ_code`, `region_id`) | `heads`, `mean_weekly_hours`, `fte`, `platform_share`, `source_tag` | FIXTURE |

`tasks.csv` gains `channel` ∈ {software, emb_driving, emb_manip, emb_fixed, emb_aerial, none} (spec v0.3 §A.2; `aiwsim.data.classify.classify_channel`, E). The registry gains P.100–P.128.

## 20. Results document additions (schema 0.4)

- `meta.headline_definition`: "FTE jobs including self-employed and platform workers"; `meta.channels_task_hours` (employment-weighted task-hour share by channel); `meta.self_employed_fte` by region; `meta.embodied_on`; `meta.cells` has 16 entries (`…|automotive` or `…|electronics`).
- `series[region]` gains `embodied_displacement_share` (percent of task-hours, percentiles), `adjacent_jobs`, `hardware_capex_bn` (produced in the region, $bn/yr), `underemployed_self_fte`, `hours_cut_self_cum`, `fleet_stock` {cls: percentiles of deployed units}, `coverage` {cls: percentiles}, `approval_share` {cls: all percentiles equal}; `meta.self_employed_fte` carries the 2024 stock by region.
- `displaced_workers_cum` now includes the self-employed margin; `flows.destinations` gains `hours_cut_self` (stock) and `self_employed_margin_cum`.
- `occupations[]` gains `automatable_share_embodied` and `displacement_embodied` {central}; `automatable_share` includes the embodied mass.
- `supply.embodiment` {cls: {clock, unit_price_usd, cost_per_hour_usd}} (percentiles).
- `channels.order` is `automation, augmentation, embodied, demand_response, reinstatement, demand_feedback, ai_investment, adjacent`.
- New section `applications`: one entry per catalogue row with `by_region[region]` = {`target_employment_2024`, `displacement_share` (percent, central, per quarter), `jobs_below_baseline`, `coverage`, `approval` (of the application's primary, first-listed class), `first_quarter` {displacement_1pct, displacement_10pct, coverage_50pct}}.
- `explain.notes` gains the embodied and self-employed-margin sentences.

## 21. Scenario schema 0.3

`levers.applications.embodiment.{driving,manipulation,fixed,aerial}_doubling_months`, `…coupling_to_software`; `levers.applications.hardware.{learning_rate, utilization_scale, unit_price_scale, ramp_max_growth_per_year}`; `levers.applications.approval.<region>` ∈ {frozen, baseline, accelerated, moratorium}; `levers.applications.platform_labor`; `levers.baseline.automation_trend`. Shocks: `approval_change` (cls, region, at, full_year, j_full), `hardware_recall` (cls, at, duration_quarters), `production_shock` (cls, at, cap_multiplier, duration_quarters). Default draws 256. Schema 0.2 scenarios stay valid.

## 22. API and static export

No new endpoints: `applications` is a section of the results document (`GET /api/results/{hash}/applications`), the levers catalogue lists the new levers with labels, and the static exporter carries the section through. Chat tools read it through `get_summary` and the results document.

# Phase 7 additions (contracts v0.8): output substitution and traded services

## 23. Input tables (`data/processed/applications/`)

| Table | Key | Columns |
|---|---|---|
| `content_categories.csv` | `cat_id` | `name`, `occ_codes` (semicolon list), `us_consumption_bn` (2024 U.S. spending at baseline prices), `eta` (own-price elasticity), `ratio0` (AI/human price 2024), `alpha0` (authenticity premium level, logit units), `intermediate` (0/1), `anchor`, `source_tag` (E, V?) |
| `services_trade.csv` | (`exporter`, `category`) | `export_bn`, `fte_per_musd`, `occ_codes`, `importers` (`REGION:weight;…`, renormalized over modelled regions), `anchor`, `source_tag` (E, V?) |

The catalogue gains `output` rows (`cls` = category id, `occ_codes` = `*cat`), `traded` rows (`cls` = trade category) and `software` rows.

## 24. Results document additions

- `series[region]`: `ai_content_share` {cat: percentiles, %}, `content_consumption_ratio` {cat: percentiles, Q/Q0}, `ai_content_revenue_bn`, `consumer_surplus_proxy_bn` (accounting quantity at baseline prices, not welfare), `traded_services_displacement_share` (% of employment).
- `applications[]` rows for output families report `displacement_share` as the share of the category's human-produced output lost vs baseline (`1 − (1 − s^AI)·Q/Q0`) and `coverage` as `s^AI`; traded rows report the traded-services displacement over target occupations; software rows report the software-channel displacement.
- `channels` order is now ten entries: automation, augmentation, embodied, output_substitution, traded_services, demand_response, reinstatement, demand_feedback, ai_investment, adjacent.
- `meta.cells`: 32 (demand × reinstatement × pass-through × hardware learning rate × authenticity {persistent, eroding}); default draws 256.
- `meta.content_categories`, `meta.export_serving_fte` by region.
- `explain.notes` gain an output-substitution note and a traded-services note.

## 25. Levers and shocks

`levers.applications.content.{authenticity: persistent|eroding, authenticity_level_scale: 0.2–3, licensing_regime: permissive|licensed|restrictive, price_sensitivity: 1–4}`, `levers.applications.trade.services_exposure_scale: 0–2`; shock `content_licensing_ruling` {at, regime} (recorded; applied in a later phase).

# Phase 8 additions (contracts v0.9): policy wiring, the Seba/RethinkX preset, the forecast scoreboard, the story layer

## 26. Story document (`GET /api/story/{hash}?region=US&companions=true`)

One reconciled reading of a run in plain language. Every number comes from the results document; nothing is computed by a model call.

```
{scenario_hash, scenario_id, scenario_name, region, horizon: [q0, qN],
 numbers: {jobs_base, jobs_gap, jobs_gap_low, jobs_gap_high, employment_pct: {p10,p50,p90}, displaced_cum, reemployed, unemployed_extra, exited,
           unfilled, laid_off, hours_cut_self, jobs_removed_by_channel: {channel: jobs}, jobs_added_by_channel: {channel: jobs},
           unemployment_peak: {quarter, extra}, gdp_pct, real_wage_pct: {p10,p50,p90}, price_index_pct, wage_share_pp, reconciliation},
 beats: [{id, title, sentence, range, sureness: {level, label, dots}, what_changes_it, chart, occupations?}],
 futures: [{name, scenario_id?, employment_pct, gdp_pct, jobs, source, description}],
 policies: [{scenario_id, name, description, jobs_delta, employment_delta_pp, unemployed_delta, real_wage_delta_pp, cost_bn_per_year, ai_tax_revenue_bn, fiscal_balance_bn, validity_note, sentence}],
 policies_against, caveats: [str], forecasts: [scoreboard rows, §28], glossary: {term: meaning}}
```

- `jobs_base` is the region's 2024 employment plus the self-employed full-time equivalents (the headline definition, §20); `jobs_gap = −employment_pct.p50 / 100 × jobs_base`, in heads. Medians are used throughout; the personal outlook and the policy deltas use the central run.
- `beats` are, in order: `jobs`, `hiring`, `young`, `pay`, `waves`, `money`, `futures`. `sureness.level` is the confidence level of the beat's metric (`high` → "we would bet on it", `medium` → "leaning this way", `low` → "a coin flip"; `dots` 3/2/1). `chart.type` ∈ {`fan` (series with p10/p50/p90 over `quarters`), `bars` (`items: [[label, value]]`, optional `reference` and `unit`), `timeline` (`items: [{app, family, first_year, share_2030, share_2040, target_jobs}]`, `start`, `end`), `regions` (`items: [[region, employment_pct, gdp_pct, rents_bn]]`), `futures`}.
- `futures`: "Gains spent back" and "Gains pocketed" are the tornado extremes of the demand multiplier (P.87); every further entry is a scenario run passed as a companion (the static export and the API pass the Seba/RethinkX preset).
- `policies`: differences of each policy scenario's central run from the baseline central run (`policies_against`), so a policy is always read against the world it modifies, whichever run the story is for. Empty when no companion runs are available. `validity_note` carries the fiscal warning (§28) when the run is outside the model's range.
- `companions=false` returns the beats without running or loading the policy scenarios and the Seba preset. With companions (the default) the service runs them at 64 draws on first use and caches them by hash.

`GET /api/brief/{hash}?format=exec|exec-html|exec-json` renders the story as the executive brief (markdown, or a self-contained HTML page with inline SVG charts). The executive brief carries no parameter codes, percentiles or section references; the technical brief (`format=md|html`) keeps them.

## 27. Personal outlook (`GET /api/outlook/{hash}?occ=&age=&region=US`)

```
{region, note, beats: [jobs, hiring, pay beats of §26], sureness_legend,
 occupation?: {occ_code, title, employment_2024, employment_pct_2030, employment_pct_2040, range_2040: [p10, p90], task_hours_automated_2040: {software, machines},
               real_wage_pct_2040, rank_percentile, verdict, how, growing_nearby: [[title, pct]], sentence},
 age?: {band, share_of_jobs_lost, employment_pct_2040, sentence}}
```

`verdict` is by rank among all occupations by 2040 employment effect (bottom 10% "among the hardest hit", 10–30% "harder hit than most", 30–70% "about average", 70–90% "less affected than most", top 10% "among the most protected"); `how` says whether the automated task-hours are mostly software, mostly machines and vehicles, or a mix. Occupation and age detail are U.S. figures; `note` says so for other regions. Static mode computes the outlook client-side from the run document with the same rules.

## 28. Policy, Seba/RethinkX preset, forecast scoreboard, levers

- **Policy wiring** (`levers.policy.<region>`, spec v0.3 §A.16): `retraining_subsidy_pct_wage` raises retraining entry and success; `wage_insurance_replacement` × `wage_insurance_years` pays displaced re-employed workers; `ubi_monthly_usd` is a transfer to every adult; `ai_tax_pct_of_ai_spend` raises AI prices by the tax and yields revenue; `work_week_hours` < 40 converts hours into heads (employment in heads rises by 40/h, pay per head falls in step); `immigration_scale` scales entrants; `financing` rules {deficit, ai_tax, payroll} decide who pays. Results: `series[region].{transfers_bn, policy_cost_bn, ai_tax_revenue_bn, fiscal_balance_bn}`, `meta.policy_on`, `meta.policy`. `meta.validity` gains `fiscal_balance_pct_gdp_2040`, `fiscal_warning` (deficit beyond 3% of GDP) and `note`; the model has no inflation or interest-rate response, so a flagged run's jobs effect is overstated.
- **Induced demand per application**: `applications.csv` gains `eta_app` (own-price elasticity of the application's output beyond the sector elasticity; Seba's "transport as a service" effect) and `whole_job` (1 when the application replaces whole jobs rather than tasks: driving roles). Lever `levers.applications.induced_demand_scale` (0–2, default 1) scales `eta_app`.
- **Seba/RethinkX preset** (`scenarios/preset-seba-rethinkx.json`): learning rate 0.25, ramp cap 1.5/yr, utilization ×1.5, unit price ×0.7, fast embodiment clocks coupled 0.7 to software, accelerated approvals where fleets already operate, eroding authenticity. Shown as a named future in the story and openable as a scenario.
- **Forecast scoreboard** (`forecasts.csv` → results `forecasts[]`): `{source, short, region, year, metric, proxy, preset_id, claimed, unit, note, source_tag, quarter, model_central, model_p10, model_p90, verdict}` with `verdict` ∈ {`within band`, `model lower`, `model higher`} from the run's p10–p90 band at the claim's quarter. `metric` ∈ {gdp_pct, tfp_pct, embodied_displacement_share, autonomous_share_of_ride_hail (robotaxi coverage), ride_hail_driver_displacement, exposed_share, young_exposed_employment_pct}. `proxy = 1` marks a claim compared with the nearest model quantity rather than the same quantity.
- **Static export** adds the policy scenarios and the Seba preset to the default run list, `story/<id>.json` (§26, policies against the exported baseline, the Seba preset as a future), `briefs/<id>.exec.md|html`, and manifest keys `story`, `exec_briefs`, `policy_scenarios`, `future_scenarios`.
