# AI Workforce Sim

An interactive, multi-region simulation of how AI models reshape the workforce and, through it, the economy, 2024–2040. U.S., EU, and Asia are first-class regions. Every parameter has a source, a central value, and a range; every output is a band, not a line.

**Status: model specification under review. No simulation or UI code yet.**

## Review package (v0.1)

| Document | What it is |
|---|---|
| [docs/model-spec.md](docs/model-spec.md) | State variables, update rules for all five layers, parameter registry with sources and ranges, calibration plan, limitations, open questions |
| [docs/data-inventory.md](docs/data-inventory.md) | Every dataset with source, license, coverage, access method, and gaps |
| [docs/wireframes.md](docs/wireframes.md) | Low-fidelity wireframes of the seven views, the shell, and the chat panel |
| [docs/risks.md](docs/risks.md) | Risks and assumptions ranked by how much they could change conclusions |
| [scenarios/schema.json](scenarios/schema.json) | JSON schema for versioned, diffable scenarios |
| [scenarios/baseline.json](scenarios/baseline.json) | The "consensus central" scenario |

## Planned architecture

- `sim/` Python 3.12, numpy/polars, pure functions, deterministic given a seed, CLI-runnable, unit-tested
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
