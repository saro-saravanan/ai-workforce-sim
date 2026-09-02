# AI Workforce Sim

An interactive, multi-region simulation of how AI models reshape the workforce and, through it, the economy, 2024–2040. U.S., EU, and Asia are first-class regions. Every parameter has a source, a central value, and a range; every output is a band, not a line.

**Status: model specification v0.2 under review. No simulation or UI code yet.** v0.2 answers the 26 findings of an adversarial review of v0.1; the change log is section 15 of the spec and v0.1 is archived in `docs/archive-model-spec-v0.1.md`.

## Review package (v0.2)

| Document | What it is |
|---|---|
| [docs/model-spec.md](docs/model-spec.md) | State variables, update rules for all five layers, parameter registry with sources and ranges, correlated Monte Carlo and structural ensemble, validation tests, limitations, open questions, change log |
| [docs/data-inventory.md](docs/data-inventory.md) | Every dataset with source, license, coverage, access method, and gaps |
| [docs/wireframes.md](docs/wireframes.md) | Low-fidelity wireframes of the seven views, the shell, and the chat panel |
| [docs/risks.md](docs/risks.md) | Risks and assumptions ranked by how much they could change conclusions |
| [scenarios/schema.json](scenarios/schema.json) | JSON schema for versioned, diffable scenarios |
| [scenarios/baseline.json](scenarios/baseline.json) | The "consensus central" scenario |

## Phase 3 (in progress)

EU-27, UK, China, Japan, South Korea, India, Taiwan, Singapore, and rest of Asia run jointly with the U.S. through a shared capability clock, regional access lags, wage tiers, adoption spillover, trade-linked demand, and AI rents by value-chain stage; 23 supply-side actors with market shares and availability; world map with drill-down, region selector, AI supply timeline. Ten regions at 200 draws run in about 18 s. Findings: `docs/findings-phase3.md`. Non-U.S. occupation structures are fixtures until the ILOSTAT/Eurostat ingest runs.

## Phase 2

Monte Carlo through a correlated copula, 2×2×2 structural ensemble, tornado sensitivity, confidence classification, cohorts with aging, labor flows, report presets with replication tests, compare and explain endpoints, what-if levers, compare view, cohort view, Sankey. `uv run aiwsim run --scenario baseline` runs 200 draws in about 9 s on 4 cores. Findings: `docs/findings-phase2.md`.

## Phase 1

U.S. national and state instance of spec v0.2, central run, three views. From a clean clone:

```
make setup && make data && make run   # then: make demo
```

`uv run aiwsim run --scenario scenarios/baseline.json` prints headline numbers and writes the results document (`docs/contracts.md` §2). Only GitHub was reachable from the build sandbox, so occupation × state and occupation × sector are labelled fixtures until `sim/aiwsim/data/ingest/` runs on a networked machine; the results document says so in `meta.data_flags`.

## Architecture

- `sim/` Python 3.12, numpy/polars, pure functions, deterministic given a seed, CLI-runnable, unit-tested (`sim/aiwsim/`)
- `api/` FastAPI: `run`, `compare`, `explain`, `sensitivity`
- `web/` Vue 3 + TypeScript (Composition API, Vite, Pinia), D3 charts, MapLibre map
- `data/` ingestion scripts with provenance for every dataset
- Claude API for scenario parsing, explanation, and insights, via tool calls into the simulation only

## Phases

1. U.S. only, static scenario, three core views, headless CLI runs
2. What-if levers, scenario compare, uncertainty bands
3. EU and Asia, AI supply-side actors, cross-region spillover
4. Chat interface, insight generation, shareable briefs
5. Polish, public demo, methodology write-up

Each phase ends with a "findings so far" note.
