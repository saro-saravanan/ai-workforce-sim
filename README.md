# AI Workforce Sim

An interactive, multi-region simulation of how AI models reshape the workforce and, through it, the economy, 2024–2040. The U.S., the EU, and Asia are first-class regions. Every parameter has a source, a central value, and a range; every output is a band relative to a world in which frontier AI froze in 2023, never a line.

**Status:** all five build phases complete; `main` carries the shipped model (specification v0.2). A **v0.3 amendment** adding embodied automation, output substitution, and traded-services channels is under review in [docs/model-spec-v0.3-applications.md](docs/model-spec-v0.3-applications.md) on branch `spec/model-v0.3`; nothing in it is implemented yet. Public demo: a static export served from GitHub Pages at `https://saro-saravanan.github.io/ai-workforce-sim/` once Pages is enabled for the repository (source: GitHub Actions); the workflow in `.github/workflows/pages.yml` builds it on every push.

![Economy view with the Ask panel](docs/screenshots/phase4-ask-insights-light.png)

## Quick start

```
make setup        # uv sync (Python 3.12 workspace) and pnpm install
make data         # fetch the pinned raw inputs (checksummed) and build the canonical tables with provenance
make run          # 200-draw, ten-region baseline → data/cache/baseline.json (~20 s on 4 cores)
make demo         # API on :8000 and the Vue app on :5173
make test         # simulation core, API, and web suites
```

`uv run aiwsim run --scenario scenarios/<id>.json` runs any scenario headless and prints the headline table. `make static` writes the serverless demo bundle to `web/public/static/`; `VITE_STATIC=1 pnpm build` in `web/` then builds the app against it.

Set `ANTHROPIC_API_KEY` in the API server's environment to enable the chat layer (`AIWSIM_CHAT_MODEL` overrides the default `claude-opus-5`). Without it, insights and briefs still work. Terminal: `cd api && uv run python -m aiwsim_api.chat "What if capability doubles every 4 months?" --hash sha256:…`.

## What it does

- **Task-level model.** ~19,000 O*NET tasks in 831 occupations, each with an ever-automatable mass, a feasibility point on a capability clock (METR task-horizon doublings), a modality, and a task-level profitability test against the worker's wage at the region's token price.
- **AI supply side.** 23 named actors across the U.S., EU, and Asia with release cadence, weights posture, prices, availability, and regional access lags; export-control and EU AI Act levers; a compute capacity constraint; rents by value-chain stage.
- **Adoption, labor flows, macro.** Bass diffusion by sector, firm size, and region, calibrated to BTOS; a hiring-first, layoffs-second labor market with cohorts that age; task-based output, prices, real wages, wage share, AI rents and net AI trade, transfers with financing rules.
- **Uncertainty as a first-class output.** 200 correlated draws re-centred on the scenario; a 2×2×2 structural ensemble over the mechanisms the literature disagrees on; one-at-a-time sensitivity; a confidence classification on every headline.
- **What-ifs as versioned JSON.** Levers, shocks, overrides, inheritance from a parent, canonical hashes; every run explains what changed, why, and how confident it is; paired comparisons on common draws.
- **Seven views plus About**: drillable world map, labor-flow Sankey, occupation heatmap, cohort view, economy dashboard, AI supply timeline, scenario compare. Light and dark, projector-legible.
- **A chat layer that never computes.** Claude turns a question into a scenario diff, runs only after confirmation, explains from the model's own channel decomposition and trace, and ranks findings from a deterministic candidate list; every number in a reply comes from a tool call into the simulation.

## Documents

| Document | What it is |
|---|---|
| [docs/methodology.md](docs/methodology.md) | The write-up: what the tool answers, the five layers, the three kinds of uncertainty, calibration, data and provenance, how to read a result, what it does not say |
| [docs/model-spec.md](docs/model-spec.md) | Specification v0.2: state variables, update rules, parameter registry, validation tests, limitations, change log, and §16 implementation notes where the code departs from the text |
| [docs/contracts.md](docs/contracts.md) | Contracts between packages: input tables, results document, API, CLI, web state, chat, insights, briefs, static export |
| [docs/data-inventory.md](docs/data-inventory.md) | Every dataset with source, license, coverage, access method, and gaps |
| [docs/risks.md](docs/risks.md) | Risks and assumptions ranked by how much they could change conclusions, with their status after the build |
| [docs/findings-phase1.md](docs/findings-phase1.md) … [phase5](docs/findings-phase5.md) | What the model said after each phase, what surprised us, what we do not trust yet |
| [docs/wireframes.md](docs/wireframes.md) | The wireframes the views were built from |
| [scenarios/](scenarios/) | `schema.json`, `baseline.json`, presets (Acemoglu 2024, Goldman Sachs 2023, IMF 2024), and the example what-if |

## Headline numbers (baseline, U.S., 2040 Q4, median and 10–90 band vs the frozen-AI counterfactual)

| Metric | Value | Sign confidence |
|---|---|---|
| Employment | −2.5% [−6.5, +1.2] | low |
| GDP | +6.8% [+4.1, +12.6] | high |
| Real wages | +3.1% [+1.9, +6.5] | high |
| Wage share | −3.5 pp [−4.8, −2.1] | high |

The employment sign is low confidence because one parameter, the demand multiplier, can flip it, and the mechanism cells disagree. At the central pace the adjustment runs through unfilled vacancies rather than layoffs, so young entrants carry about half of the jobs below baseline. See `docs/findings-phase5.md`.

## Architecture

- `sim/` Python 3.12, numpy/polars, pure functions, deterministic given a seed, CLI-runnable, unit-tested (`aiwsim` package)
- `api/` FastAPI: scenarios, run, results, compare, explain, sensitivity, levers, regions, actors, chat, insights, brief, static export
- `web/` Vue 3 + TypeScript (Composition API, Vite, Pinia), D3 charts; no React
- `data/` canonical tables with a provenance record per dataset; ingestion scripts for every source, real where reachable, labelled fixtures otherwise
- Claude API for scenario parsing, explanation, and insights, through tool calls into the simulation only

## Data caveats

The build sandbox could reach only GitHub, so occupation tasks, exposure, employment, wages, and projections are real (Eloundou et al. replication data, OEWS 2021, BLS EP 2020–30, METR, Natural Earth) while occupation × state, occupation × sector, non-U.S. occupation structures, trade weights, and cohort joint distributions are labelled fixtures. Every results document says so in `meta.data_flags`, the map hatches fixture regions, and the ingest scripts in `sim/aiwsim/data/ingest/` replace the fixtures on a networked machine.

## Phases

1. U.S. only, static scenario, three core views, headless CLI runs
2. What-if levers, scenario compare, uncertainty bands
3. EU and Asia, AI supply-side actors, cross-region spillover
4. Chat interface, insight generation, shareable briefs
5. Polish, public demo, methodology write-up

Each phase ended with a "findings so far" note.
