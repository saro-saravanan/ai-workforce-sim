# AI Workforce Sim

An interactive, multi-region simulation of how AI models reshape the workforce and, through it, the economy, 2024–2040. The U.S., the EU, and Asia are first-class regions. Every parameter has a source, a central value, and a range; every output is a band relative to a world in which frontier AI froze in 2023, never a line.

**Status:** nine build phases complete; `main` carries the shipped model (specification v0.2 plus the **v0.3 amendment**, [docs/model-spec-v0.3-applications.md](docs/model-spec-v0.3-applications.md), which adds embodied automation, output substitution and traded-services channels, policy wiring, and the Seba/RethinkX presets). Phase 8 added the **Story** view (one reconciled set of numbers, seven findings, named futures, policy runs, a personal outlook, an executive brief, and a scoreboard of named forecasts). Phase 9 implemented the priority plan of an [adversarial review](docs/adversarial-review-phase8.md): a **backtest** against 2024–2026, the macro **closure as an ensemble axis** (64 cells), a convergence test, a regional decomposition with a U.S.-closed configuration, threshold-seed and classifier checks, embodied cost floors, balanced-budget policy financing, an entrant supply response with a market-clearing wage variant, and a one-page [model statement](docs/current-model.md); see [docs/findings-phase9.md](docs/findings-phase9.md). Phase 9b closed the items the review left open: real BLS OEWS May 2025 occupation-by-sector and state tables fetched by a GitHub Actions workflow (the build environment cannot reach BLS or BEA), a 20-sector layer with input-output propagation ready for the BEA use table, a 2026 hold-out, an exposure-source swap (AIOE), a labelled classifier audit with rules v3, and a robotaxi fleet series; see [docs/findings-phase9b.md](docs/findings-phase9b.md). Public demo: a static export served from GitHub Pages at `https://saro-saravanan.github.io/ai-workforce-sim/`; the workflow in `.github/workflows/pages.yml` builds it on every push to `main`.

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

- **Task-level model.** ~19,000 O*NET tasks in 831 occupations (employment and wages from OEWS May 2025, placed in 20 NAICS sectors and 51 states from the same source), each with an ever-automatable mass, a feasibility point on a capability clock (METR task-horizon doublings), a modality, and a task-level profitability test against the worker's wage at the region's token price.
- **AI supply side.** 23 named actors across the U.S., EU, and Asia with release cadence, weights posture, prices, availability, and regional access lags; export-control and EU AI Act levers; a compute capacity constraint; rents by value-chain stage.
- **Adoption, labor flows, macro.** Bass diffusion by sector, firm size, and region, calibrated to BTOS; a hiring-first, layoffs-second labor market with cohorts that age; task-based output, prices, real wages, wage share, AI rents and net AI trade, transfers with financing rules.
- **Uncertainty as a first-class output.** 200 correlated draws re-centred on the scenario; a 2×2×2 structural ensemble over the mechanisms the literature disagrees on; one-at-a-time sensitivity; a confidence classification on every headline.
- **What-ifs as versioned JSON.** Levers, shocks, overrides, inheritance from a parent, canonical hashes; every run explains what changed, why, and how confident it is; paired comparisons on common draws.
- **Application layer (v0.3).** Every task group belongs to one channel: software, driving, mobile manipulation, fixed automation, aerial, or none. Embodied classes carry hardware unit cost on a learning curve, a production ramp, approval paths by region, and deployment coverage; ten catalogued applications (robotaxis to humanoids) report their gates. Self-employed and platform workers are in the headline.
- **Story and outlook (Phase 8).** A landing view that tells the run as seven findings with a chart, a likely range, a sureness label and "what changes it" for each; a jobs ledger and a people ledger kept apart and reconciled; named futures ("gains spent back", "gains pocketed", the Seba/RethinkX preset); policy runs (retraining, wage insurance, a basic income with an AI tax, a 36-hour week) read against the baseline with a fiscal-validity warning; "Your outlook" by occupation and age; an investment-versus-returns section that puts the hyperscalers' capex against what AI producers earn and what the economy gains; an executive brief with inline charts; and a scoreboard of named forecasts with a verdict on every run.
- **Robustness (Phase 9).** A backtest table and view (model 2024Q1–2026Q2 against BTOS adoption, Challenger AI-cited cuts, industry revenue, capex, graduate unemployment and software postings, with calibration targets marked); the macro closure (demand feedback on or off) as a sixth structural axis, so the Story's two futures are the closure medians and its range is "the range of the model's assumptions"; `aiwsim convergence`, `aiwsim regional` and `aiwsim diag` for seed noise, the regional decomposition of the U.S. headline and the task engine's resolution; a U.S.-closed configuration and a ramp-allocation lever; cost floors under the hardware curves; a surcharge-financed basic income with the deficit version isolated behind a validity flag; an entrant supply response and a market-clearing wage variant read into the pay beat.
- **Ten views plus About**: story, your outlook, backtest, drillable world map, labor-flow Sankey, occupation heatmap, cohort view, economy dashboard, AI supply timeline, scenario compare. Light and dark, projector-legible.
- **A chat layer that never computes.** Claude turns a question into a scenario diff, runs only after confirmation, explains from the model's own channel decomposition and trace, and ranks findings from a deterministic candidate list; every number in a reply comes from a tool call into the simulation.

## Documents

| Document | What it is |
|---|---|
| [docs/methodology.md](docs/methodology.md) | The write-up: what the tool answers, the five layers, the three kinds of uncertainty, calibration, data and provenance, how to read a result, what it does not say |
| [docs/model-spec.md](docs/model-spec.md) | Specification v0.2: state variables, update rules, parameter registry, validation tests, limitations, change log, and §16 implementation notes where the code departs from the text |
| [docs/contracts.md](docs/contracts.md) | Contracts between packages: input tables, results document, API, CLI, web state, chat, insights, briefs, static export |
| [docs/data-inventory.md](docs/data-inventory.md) | Every dataset with source, license, coverage, access method, and gaps |
| [docs/risks.md](docs/risks.md) | Risks and assumptions ranked by how much they could change conclusions, with their status after the build |
| [docs/findings-phase1.md](docs/findings-phase1.md) … [phase9](docs/findings-phase9.md), [phase9b](docs/findings-phase9b.md) | What the model said after each phase, what surprised us, what we do not trust yet |
| [docs/adversarial-review-phase8.md](docs/adversarial-review-phase8.md) | The end-of-Phase-8 adversarial review: what a veteran would attack, ranked, with diagnostics and a priority plan |
| [docs/current-model.md](docs/current-model.md) | The model on one page: what it is, the chain of equations, what is fitted and to what, what is assumed, how it is tested, how to read a number |
| [docs/convergence.md](docs/convergence.md), [regional-decomposition.md](docs/regional-decomposition.md), [diagnostics-phase9.md](docs/diagnostics-phase9.md), [holdout-2026.md](docs/holdout-2026.md), [classifier-audit-sample.md](docs/classifier-audit-sample.md), [classifier-audit-agreement.md](docs/classifier-audit-agreement.md) | Diagnostics: seed noise by draw count, the U.S. headline by regional configuration, threshold-seed sensitivity, the 2026 hold-out, the labelled classifier audit and the rules' agreement with it |
| [docs/wireframes.md](docs/wireframes.md) | The wireframes the views were built from |
| [scenarios/](scenarios/) | `schema.json`, `baseline.json`, presets (Acemoglu 2024, Goldman Sachs 2023, IMF 2024, Seba/RethinkX 2017 and 2026), policy runs, behavioural variants, the U.S.-closed configuration, and the example what-if |

## Headline numbers (baseline, U.S., 2040 Q4, median and 10–90 band vs the frozen-AI counterfactual)

| Metric | Value | Sign confidence |
|---|---|---|
| Employment | −8.2% [−11.3, −5.1] (about 15.8 million jobs against the 194 million there would have been in 2040) | high |
| GDP | +4.3% | high |
| Real wages | +2.0% [+1.0, +3.9] | high |
| Wage share | −5.7 pp | high |

In levels: about 167 million jobs today (OEWS May 2025 base, including gig and freelance work), 194 million by 2040 without further AI progress, 178 million with it (likely 172 to 184 million), so more jobs than today and fewer than there would have been. Most of the gap is hiring that never happens: about 8.6 million positions are never offered to new entrants against 3.1 million layoffs, the layoff share fitted to the AI-cited job cuts employers announced in 2025 and the first half of 2026 (Challenger, Gray & Christmas). The range is the range of the model's assumptions: the macro closure is a structural axis, and the median is −7.9% with demand feedback on and −8.6% with it off; the 64 mechanism cells span −11.5% to −4.2% and agree on the sign. Phase 9b's real sector tables corrected the labour-cost share that drives prices (labour's share of gross output, 0.45, in place of the single-sector value-added share, 0.58), which is why the GDP and real-wage effects are about a third smaller than in Phase 9 while the employment effect is a point larger. The backtest against 2024–2026 says adoption is within survey noise, the model's layoffs start a year early, revenue is within the fitted range, and a fit to 2025 alone under-predicts 2026. Robots and vehicles reach 5% of task-hours by 2040 at central assumptions. See `docs/findings-phase9b.md`.

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
6. v0.3: embodied automation (robotaxis, robots), self-employed and platform workers
7. v0.3: output substitution (AI-made content), traded services, full application catalogue
8. Story layer: one reconciled set of numbers, seven findings in plain language, named futures (including two Seba/RethinkX presets: the 2017 transport claims and the 2024–2026 humanoid and TaaS claims), policy runs, a personal outlook, an executive brief, and a scoreboard of named forecasts

Each phase ended with a "findings so far" note.
