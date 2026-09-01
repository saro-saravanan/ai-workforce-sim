# Findings so far — Phase 1 (U.S., central run)

Date: 2026-09-01. Spec v0.2. Scenario: `baseline` ("Consensus central"), one central run, no Monte Carlo yet. Every number below is relative to the frozen-AI baseline (no frontier progress after 2023 Q4) and comes from `data/cache/baseline.json`; the mechanism trace is in the results document's `channels` and `explain` sections.

## What the model currently says

| Quarter | Capability (50% horizon) | Adoption (employment-weighted) | Employment | Real wages | GDP | TFP | Wage share |
|---|---|---|---|---|---|---|---|
| 2027 Q4 | ~50 h tasks | 50% | −0.4% | 0.0% | +1.4% | +0.4% | −0.6 pp |
| 2030 Q4 | ~3,300 h tasks | 76% | −1.9% | +1.2% | +3.0% | +2.3% | −1.5 pp |
| 2035 Q4 | saturated | 95% | −2.7% | +3.7% | +5.4% | +5.1% | −2.2 pp |
| 2040 Q4 | saturated | 99% | −3.3% | +4.8% | +6.3% | +6.4% | −2.4 pp |

Channel decomposition of the 2040 employment effect (sequential switch-on, percentage points): automation −8.8; augmentation −1.2; demand response +3.3; reinstatement +1.5; demand feedback +1.3; AI investment +0.6. Net −3.3.

Three things the central run says that a static report cannot:

1. **Displacement arrives through hiring, not layoffs.** At the central pace, the labor demand gap never exceeds what natural occupational attrition (about 2.5% a quarter) can absorb, so 100% of the 6.0M jobs below baseline by 2040 are positions not refilled and 0% are layoffs. That matches the observed pattern in 2025 and 2026 (young workers in exposed occupations hired less; aggregate employment flat) and it means the visible signal of AI displacement will be entry-level hiring for years before it is unemployment.
2. **The demand response is the largest offset, and it is a parameter nobody has measured for AI.** Cheaper output raising demand recovers 3.3 pp of the 8.8 pp automation loss. That rests on sector demand elasticity (0.8 in the single-sector fixture) and price pass-through (0.7). Both are structural-ensemble axes in Phase 2; the sign of the net employment effect in elastic sectors depends on them.
3. **Exposed but not yet hit is where the employment is.** The occupations with the highest realized displacement in 2030 are small technical ones (programmers, data scientists, systems administrators at 11 to 12% of task-hours). The large gaps are Office Clerks (2.6M jobs, 45% automatable, 8% realized), Customer Service Representatives (2.8M, 31%, 6%), and General and Operations Managers (3.0M, 30%, 5%). The heatmap's below-diagonal mass is the story.

Employment-weighted ever-automatable share of U.S. task-hours: 30%. Realized AI share of task-hours by 2040: 8%. The gap between those two numbers is the substitution share (0.45 rising slowly), the intensity ceiling (0.7), and the task-level profitability test, in that order.

## What surprised me

- **The first run collapsed, and the reason was instructive.** Before two fixes, the model produced GDP −27% and real wages −62% by 2040. The wage rule had no mean reversion, so a persistent excess supply pushed wages down every quarter forever, and the demand feedback counted lost wages but not the profits and cost savings that offset them. Both are now the spec's own equations (a wage curve with partial adjustment; household income including profits at a lower marginal propensity to consume). The lesson for Phase 2 is that the demand-feedback loop is where an ensemble will show the widest structural disagreement.
- **The compute capacity constraint never binds** in the central run (price multiplier stays at 1.0). Token demand from 8% of task-hours is small against a capex path that reaches roughly $720bn a year by 2026. The constraint matters only in the fast-clock, high-intensity corner, which is exactly where the supply-chain shock scenario lives.
- **AI spend is small relative to the labor it replaces**: about $60bn a year by 2040 against a wage bill in the trillions, because inference prices fall to the floor within three years. The cost layer stops mattering by 2028 and integration cost and the intensity ceiling take over as the brakes. That was the v0.1 review's prediction and the model confirms it.

## What I do not trust yet

1. **The capability clock.** The central doubling time (5 months) puts month-long tasks inside the 50% horizon by 2030 and saturates the clock by 2032. That is METR's own extrapolation, but METR also says horizons above 8 hours rest on 5 of 228 tasks. The domain-transfer discount (0.7 and 0.5) and the ever-automatable mass are doing all the work of keeping the model sane, and both are estimates.
2. **Feasibility points without usage anchoring.** The Anthropic Economic Index task-usage data was unreachable from the build sandbox, so E1 tasks are spread over 2024 to 2025 by a deterministic hash and E2/E0 use class offsets. Running `sim/aiwsim/data/ingest/aei.py` on a networked machine replaces this.
3. **The state map is a fixture.** Every state has the national occupational mix scaled by a population proxy, so the map shows size, not geography. The OEWS state ingest fixes it; the map carries a fixture badge until then.
4. **Single sector.** Demand elasticity, labor cost share, and friction are one number each. Sector heterogeneity is the point of the demand-response channel and it is absent until the OEWS industry matrix is ingested.
5. **Calibration is thin.** Only Bass `q` and the small/mid hurdle were fitted, to three BTOS points and one growth increment, on a grid. The fit reproduces firm-weighted adoption of 11% in late 2025 and employment-weighted 30%, close to the observed 10% and 32%, but the identification is weak and the wording break is a level shift by assumption.
6. **Keyword classifiers.** Modality, presence, and regulatory use case come from regex rules over task text. They are transparent and tagged E, and they are wrong for some tasks. O*NET Work Context replaces presence on ingest.
7. **Occupation grid.** The simulation runs on all 831 six-digit occupations; the spec's clustering rule (§1.1) yields 450 clusters, not ~120, because minor-group merging bottoms out at 214 even with no tolerance. An opt-in stage that merges within major groups reaches 177 to 284 depending on tolerances. The central run is 0.5 s at full resolution, but 200 Monte Carlo draws would take about 100 s against a 10 s budget. Phase 2 either vectorizes across draws or adopts the coarser clustering; that is a decision for the owner, not a bug.

## Runtime and reproducibility

Central run 0.49 s; with the six-channel decomposition 2.4 s; calibration grid 36 runs in about 20 s. Same scenario hash and seed give bit-identical output. `make setup && make data && make run` reproduces everything in this note from a clean clone, with the fixture flags shown in `meta.data_flags`.
