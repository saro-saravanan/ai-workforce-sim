# AI Workforce Impact Model — Specification v0.2 (for review)

Status: **draft for review, no simulation code written.** Supersedes v0.1 (kept at `docs/archive-model-spec-v0.1.md`). Section 15 maps every item of the v0.1 adversarial review to the change made.

Scope: the full model as it will exist at Phase 3 (U.S., EU, Asia). Phase 1 implements the U.S. instance of the same equations.

Decisions already confirmed with the owner (2026-09-01):

| Decision | Choice |
|---|---|
| Occupation × sector grid | ~120 occupation clusters × ~20 sectors |
| Time step | Quarterly, 2024 Q1 → 2040 Q4 (68 steps) |
| Regions at Phase 3 | U.S. (50 states + DC), EU-27 + UK, China, Japan, South Korea, India, Taiwan, Singapore, Rest of Asia |
| Macro layer | Reduced-form, with explicit AI capex channel; not general equilibrium |
| Capability metric | Composite index (task-horizon + benchmark), actors from public data only |
| Calibration | Adoption and prices fitted; labor layer prior-driven and labelled as such |
| Baseline | No frontier AI progress after 2023 Q4 |
| Cohorts | Age (4) × education (4) × income decile (10), jointly fitted from CPS |
| Runtime | Central run < 1 s; 200-draw Monte Carlo < 10 s; cached by scenario hash |
| Data | Open sources only |
| Tooling | Python 3.12 + uv + polars/numpy; Vue 3 + TS + pnpm; monorepo |

Decisions taken on the six reviewer questions (§13), 2026-09-01, by the modeler on the owner's instruction:

| Question | Decision | Reason |
|---|---|---|
| 1. Capability units in the UI | Horizon units ("AI completes 8-hour tasks at 50% reliability"), with the abstract index in tooltips | Explains itself to a non-technical viewer; the METR definition is the only public one with a time series |
| 2. Ever-automatable defaults | Keep 0.9 / 0.7 / 0.25 for E1 / E2 / E0 | E1 near-certain given observed usage; E2 needs tooling that is arriving; E0 non-zero because labels are GPT-4-era, but low because most E0 non-physical work is presence-bound. Copula correlation across the three keeps the aggregate band honest |
| 3. Recession shock sign on adoption | Neutral default; lever range from capex-cut (−) to labor-cost-pressure (+) | Literature disagrees; a neutral default avoids encoding a side |
| 4. U.S. states in Phase 1 | Yes | The map is the first view a viewer sees; state OEWS data is in the same release; IPF construction is cheap |
| 5. Presets first-class in compare | Yes | "Why does Goldman say 7% and Acemoglu 0.7%" is the most useful demo the tool can give |
| 6. Structural ensemble on by default | Yes, with a "central mechanisms" toggle under Advanced, labelled as narrower than the model's real uncertainty | A single-mechanism band is the false precision the brief forbids |

Phase 1 scope adjustment: cohorts and aging (§1.4, §5.6) move to Phase 2 with the cohort view, so Phase 1 tracks occupation × sector × state. Nothing in the equations changes; the cohort dimension is added, not re-derived.

Notation: every parameter has an ID (`P.xx`), a central value, a range, a source, and a provenance tag: `S` sourced, `D` derived from cited data by a stated transformation, `E` **estimated by us** (flagged and exposed as a lever). All cited numbers were checked against primary sources on 2026-09-01; the data inventory records verification status.

---

## 0. The whiteboard version

**AI capability rises on an exponential clock; each task has a probability of ever being automatable by software and, if so, a point on the clock at which it becomes feasible; firms hand over the tasks that are both feasible and cheaper than the worker, on an S-curve gated by benefit, friction, regulation, and access; automation and augmentation both lower unit costs, which raises output demand, so employment falls only where cost savings outrun demand; displaced workers flow to other occupations, retraining, or exit depending on who they are, and cohorts age; wages respond to excess supply and are deflated by falling prices; output, profits, AI rents by value chain, taxes, and inequality follow; and every effect is reported as a band relative to a world where AI froze in 2023, across parameter draws and across the mechanisms the literature disagrees on.**

```
 AI SUPPLY                 TASKS                    FIRMS                    WORKERS                 ECONOMY
 ┌──────────┐  C_t, p   ┌────────────┐  S,G (profit- ┌────────────┐  D,U     ┌────────────┐  ΔL,Δw  ┌────────────┐
 │ actors,  │ ────────▶ │ a_k: ever  │  able only)   │ ceiling ×  │ ───────▶ │ flows by   │ ──────▶ │ task-based │
 │ prices,  │ compute   │ θ_k: when  │ ────────────▶ │ speed      │          │ occupation │         │ output,    │
 │ regimes, │ capacity  │ κ_k < w    │               │ + entrants │          │ cohort,    │         │ prices,    │
 │ rents    │ ◀──────── └────────────┘               └────────────┘          │ aging      │         │ rents,     │
 └──────────┘  token demand                               ▲                  └────────────┘         │ taxes,     │
      ▲                                                   │ spillover              │ demand        │ inequality │
      │ regulation by use case, export controls,          │                        ▼ feedback      └─────┬──────┘
      └───────────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 1. Indices, sets, and dimensions

| Symbol | Set | Size (Phase 3) | Source of the list |
|---|---|---|---|
| `t` | quarters 2024Q1..2040Q4 | 68 | — |
| `r` | regions | 10 (US, EU, UK, CN, JP, KR, IN, TW, SG, RoA) | — |
| `g` | sub-regions | 51 U.S. states+DC; 27 EU members; others = 1 | Census, Eurostat |
| `o` | occupation clusters | ~120 | O*NET-SOC 2019 → clusters (§1.1) |
| `s` | sectors | 20 + 1 "AI production" (§1.2) | NAICS 2-digit merged |
| `k` | tasks | ~19,000 O*NET task statements | O*NET 31.0 |
| `u` | use-case class for regulation | 3 {high-risk, transparency-only, unregulated} | EU AI Act Annex III mapped to task families |
| `c` | cohorts = age × education × income decile | 4 × 4 × 10 = 160 | CPS |
| `f` | firm-size class | 3 (1–49, 50–499, 500+) | Census BTOS, SUSB |
| `a` | AI actors | ~26 (incl. NVIDIA, TSMC, ASML) | §3.1 |
| `v` | value-chain stages | 4 {model, compute/cloud, chips/equipment, integration} | §6.3 |
| `j` | labor-market state | 7 (§5.1) | — |
| `m` | mechanism variant (structural ensemble) | 8 (§7.4) | — |
| `d` | Monte Carlo draw | 200 default | — |

### 1.1 Occupation clusters
As v0.1: keep every 6-digit SOC with U.S. employment ≥ 300k; merge within 4-digit families when Eloundou exposure differs by < 0.1 and median wage by < 20%; never across major groups. Deterministic script, thresholds as parameters, crosswalk versioned. EU and Asia mapped through ISCO-08 → SOC 2010 → SOC 2018 with per-cluster mapping quality scored.

### 1.2 Sectors
NAICS 2-digit, 31–33, 44–45, 48–49 merged; plus an **AI production** sector (data-center construction and operation, model development; NAICS 5182, 5415 partial, 2371 partial) whose employment is driven by capex and AI spend (§5.7), not by the adoption layer.

### 1.3 Sub-regional employment
OEWS publishes occupation × industry nationally and occupation × state, not the three-way cross. State-level `N_{o,s,g}` is built by iterative proportional fitting of the national occupation × industry matrix to state occupation totals and state industry totals (QCEW). This is an assumption and is flagged on the map.

### 1.4 Cohorts and aging
Age bands {16–24, 25–44, 45–54, 55+}; education {< HS, HS, some college, BA+}; individual-earnings decile within region. Joint distribution `π_{o,c}` fitted once from five pooled CPS ASEC years by IPF against OEWS wage distributions and ACS age × education marginals per occupation. **Aging**: each quarter a share `1 / (band width in quarters)` of each age band moves to the next band (16–24: 1/36 per quarter; 25–44: 1/80; 45–54: 1/40), carrying its labor-market state and occupation; education is fixed; income deciles are re-ranked each year on simulated earnings. Non-U.S. regions use EU-LFS microdata where available and marginals-only with imputed deciles elsewhere, flagged.

---

## 2. Layer 1 — Task feasibility

### 2.1 What changed from v0.1
v0.1 put every task on the METR horizon scale and made every non-physical task feasible by 2028. v0.2 separates three things: **whether** a task is ever automatable by software-only AI (`a_k`), **when** it becomes feasible on the capability clock (`θ_k`, anchored to observed usage), and **whether it pays** (`κ_k < w`, §2.4). The METR series is used only as the *trend* of the clock, with a domain-transfer discount for non-software work.

### 2.2 Static task attributes (computed once at ingestion)

- `w_{o,k}` task weight, `∝ importance × relevance × frequency`, normalized within occupation. `[D]`
- `x_k ∈ {E0, E1, E2}` Eloundou exposure label; fallback to occupation-level AIOE rescaled, flagged. `[S]`
- `m_k ∈ {software/analytical, other cognitive, interpersonal, physical}` modality from O*NET GWA mapping. `[D]`
- `π_k ∈ [0,1]` **presence requirement**, from O*NET Work Context items "Face-to-Face Discussions", "Physical Proximity", "Deal With External Customers", "Performing for or Working Directly with the Public", rescaled. `[D]`
- `u_k` regulatory use-case class: high-risk if the task family is in EU AI Act Annex III (recruitment/selection, worker management and evaluation, creditworthiness, education access/assessment, essential services eligibility, law enforcement, migration, justice); transparency-only for content generation facing the public; unregulated otherwise. `[D]`
- `a_k ∈ [0,1]` **ever-automatable mass**: probability that software-only AI can perform the task unsupervised at any capability level within the horizon.

$$a_k = a_{\text{base}}(x_k)\,\big(1 - \pi_k\big)^{\,\lambda_\pi}\quad\text{for non-physical } k;\qquad a_k = a_{\text{phys}} \text{ for physical } k \text{ (robotics track, §3.5)}$$

`a_base(E1) = 0.9`, `a_base(E2) = 0.7`, `a_base(E0) = 0.25`, presence exponent `λ_π = 1.5` (`P.20–P.23`, `E`, wide ranges). The E0 mass is deliberately non-zero because Eloundou labels are GPT-4-era; the presence term is what keeps in-person work out.

- `θ_k` **feasibility point on the clock**, anchored to observation:
  - Tasks with observed AI usage: the Anthropic Economic Index gives task-level usage shares by release. If a task's usage share exceeded `P.24` (central 0.5× its employment-weighted share, `E`) in a release with data window quarter `t*`, then `θ_k = C_{t*}` (feasible at the capability that existed then). Directive-vs-collaborative split in AEI (automation-type conversations) is used as the stronger signal where present.
  - Tasks without observed usage: `θ_k = C_{2026Q2} + Δ(x_k, m_k)` with `Δ(E1) = 1`, `Δ(E2) = 3`, `Δ(E0) = 6` doublings, plus `+1` for high "Consequence of Error" (reliability shift). `P.25–P.28`, `E`.
- `s_k` softness, one per modality, `P.15`.
- `σ_{k,t}` substitution share, from AEI automation/augmentation by task family (`P.16`), drift lever with a range including zero (`P.17`).
- `n_k` tokens per task-unit, **growing with the feasibility point**: `n_k = n_0(m_k)·2^{γ_n(θ_k − C_{ref})}` (`P.08`, `P.29`; agentic tasks at longer horizons consume more tokens).

### 2.3 Feasibility update rule

Effective clock for task `k` in region `r`: `C^{eff}_{k,r,t} = C_{ref} + g_{m_k}\,(C_{r,t} − C_{ref})`, with domain-transfer factor `g_m` (`P.34`: software 1.0; other cognitive 0.7; interpersonal 0.5; `E`, lever). Then

$$F_{k,r,t} = a_k\;\Lambda\!\left(\frac{C^{eff}_{k,r,t} - \theta_k}{s_k}\right)$$

`F` saturates at `a_k`, so exposure at `C → ∞` equals `Σ_k w_{o,k} a_k`, which is informative and is the heatmap's x-axis.

### 2.4 Profitability at the task level

Cost to perform one task-unit by AI in sector `s`, region `r` (§3.4): `κ_{k,s,r,t}`. Labor cost of the same task-unit: `w_{o,r,t}·w_{o,k}/h` per worker-quarter of occupation `o`, written `ℓ_{o,k,r,t}`. Profitable-feasible share:

$$\Pi_{k,o,s,r,t} = F_{k,r,t}\;\Lambda\!\left(\frac{\ln \ell_{o,k,r,t} - \ln \kappa_{k,s,r,t}}{b_\kappa}\right)$$

with softness `b_κ` (`P.35`). Occupation-level substitutable and augmentable shares are **profitable-feasible** shares:

$$S_{o,s,r,t} = \sum_k w_{o,k}\,\sigma_{k,t}\,\Pi_{k,o,s,r,t},\qquad G_{o,s,r,t} = \sum_k w_{o,k}\,(1-\sigma_{k,t})\,F_{k,r,t}$$

Augmentation `G` uses feasibility only (a tool that helps is used when cheap enough for the firm, §4), substitution `S` requires the task-level cost test. A feasible task that is not cheaper than a low-wage worker is not displaced. Cost-saving share for the macro layer (§6.1): `ζ_{o,s,r,t} = Σ_k w_{o,k} σ_k Π_k (1 − κ_k/ℓ_{o,k})`.

---

## 3. Layer 2 — AI capability supply

### 3.1 Actors
As v0.1, from public data only, with the addition of TSMC and ASML as chokepoint actors and NVIDIA as compute. Each lab actor has `region_a`, frontier lag `λ_a`, cadence `κ_a`, weights posture `ω_a`, price `p_a(t)`, availability `V_{a,r}(t) ∈ [0,1]`. **New**: a public value-chain gross-margin record per stage (§6.3).

### 3.2 Global frontier capability (the clock)

`C_t` in doublings of the METR 50% horizon on software tasks. Anchors `[S]`: GPT-5 (Aug 2025) ≈ 7.1; Claude Mythos Preview (Mar 2026) ≥ 16 h ≈ 9.9 with a 95% interval of 8.5–55 h; METR warns horizons above ~8 h rest on 5 of 228 tasks. The clock saturates for modelling purposes at `C_max = 20` (`P.36`) because beyond that every `θ_k` has been passed and only `a_k` binds.

$$C_{t+1} = \min\!\big(C_{max},\; C_t + 3/\tau_t + \epsilon^C_t\big),\qquad \tau_t = \tau_0 (1+\gamma)^{(t-t_0)/4}$$

`τ_0` (`P.01`, central 5 months, range 3–12), drift `γ` (`P.02`), noise (`P.03`). Frontier breakthrough shock adds `ΔC`. Optional revenue feedback lever (off by default).

### 3.3 Regional available capability and price

$$C_{r,t} = \max_{a:\;V_{a,r}(t) \ge v_{min}} \big[C_t - \lambda_a - \delta^{reg}_{r,t}\big]$$

Availability no longer scales the index; it gates which actors count (`v_min`, `P.37`) and enters adoption as a multiplier `φ^{avail}_{r} = max_a V_{a,r}` (§4.2).

Price at fixed capability declines at `ρ` per year (`P.04`) toward a floor; open-weights compression as v0.1 (`P.05–P.06`).

### 3.4 Cost floor, compute capacity, and effective task cost

Compute capacity in region-serving terms: `K_t = Σ_{τ≤t} capex_τ · e_τ` where `e_τ` is tokens per dollar of capex, improving at `P.07` per year, depreciated over `P.38` quarters. Token demand `T_t = Σ_{k,s,r} n_k × (AI task-units)` from the adoption layer. Capacity price multiplier:

$$\text{mult}_t = \max\!\big(1,\;(T_t/K_t)^{\xi}\big),\qquad \xi \in P.39$$

so a demand overshoot raises inference prices rather than being served for free. The supply-chain shock reduces `K_t` and `e_τ`. Effective cost per task-unit:

$$\kappa_{k,s,r,t} = \max\big(p_{r,t}(\theta_k),\,\text{floor}_t\big)\,\text{mult}_t\,n_k \;+\; I_{s}/H \;+\; \chi_{u_k,r,t}$$

Compliance premium `χ` is now indexed by **use-case class**, not sector (§4.2).

### 3.5 Robotics frontier
As v0.1: separate clock `C^{phys}` (`P.19`) applied to physical tasks with `a_phys` (`P.59`).

### 3.6 Actor market shares (endogenous)
Within region `r`, lab actor market share for capability tier `C'`:

$$m_{a,r,t} = \frac{V_{a,r}\,\exp\big(\beta_m\,[\,(C_{a,t} - C') - \psi_p \ln p_{a,t}\,]\big)}{\sum_{a'} V_{a',r}\,\exp(\cdots)}$$

(`P.57–P.58`, `E`, fitted loosely to Ramp AI Index vendor shares and public revenue estimates). Shares feed the rent allocation (§6.3), so an open-weights shock moves rents through prices *and* shares.

---

## 4. Layer 3 — Adoption and diffusion

### 4.1 State
`A_{s,f,r,t}` share of firms adopting; `ι_{s,f,r,t}` intensity within adopters; `A^{max}_{s,f,r,t}` the ceiling (share of firms for whom adoption pays).

### 4.2 Update rules

Net benefit per worker-quarter for the marginal firm, using profitable-feasible shares:

$$B_{s,f,r,t} = \sum_o e_{o,s,r}\,\bar w_{o,r,t}\,\big[\zeta_{o,s,r,t} + \psi\,G_{o,s,r,t}\big] - \sum_o e_{o,s,r}\sum_k w_{o,k}\,(1-\sigma_k)\,F_{k,r,t}\,\kappa_{k,s,r,t}$$

(the substitution term is already net of AI cost through `ζ`; the augmentation term pays for its own tools).

**Ceiling** (benefit-driven, heterogeneous firms): `A^{max} = Λ((B − B*_{f})/b)` with size-specific hurdle `B*_f` (`P.46`) and dispersion `b` (`P.47`). **Speed** (friction-driven):

$$A_{t+1} = A_t + \Big[p + q\,\tfrac{A_t}{A^{max}_t} + q^{\times}\!\sum_{r'\neq r}\omega_{rr'}\tfrac{A_{s,f,r',t-L}}{A^{max}_{s,f,r',t-L}}\Big]\big(A^{max}_t - A_t\big)\,\phi_s\,\phi_f\,\phi^{reg}_{u(s)}\,\phi^{avail}_r \;+\; \text{entry}_{s,f,r,t}$$

- `p` fixed at the Bass meta-analysis prior (`P.41`, not fitted); `q` fitted (`P.42`); `q^×` fixed prior (`P.43`) because it is not identifiable separately from the shared capability path.
- `φ^reg_u` applies only to the share of the sector's task-units in high-risk use-case classes: `φ^{reg}_{u(s)} = 1 − (1 − φ^{HR})·share^{HR}_s − (1 − φ^{T})·share^{T}_s` (`P.32a`, `P.32b`). Automating back-office or analytical tasks in "employment-related" sectors is **not** high-risk and is not penalized.
- **AI-native entrants**: `entry = ε_{s,f}·(A^{ent} − A_t)` with firm entry rate `ε` from BDS (`[S]`) and entrant adoption `A^{ent}` from BTOS young-firm cuts (`P.52`, `[D]`). Entrants carry no integration cost (`I_s = 0` in their `B`).
- Intensity ramps to `ι^{max}` (`P.50–P.51`).

Realized AI shares in occupation `o`, sector `s`, region `r`:

$$D_{o,s,r,t} = \sum_f \pi_{s,f}\,A_{s,f,r,t}\,\iota_{s,f,r,t}\,S_{o,s,r,t},\qquad U_{o,s,r,t} = \sum_f \pi_{s,f}\,A_{s,f,r,t}\,\iota_{s,f,r,t}\,G_{o,s,r,t}$$

AI task-units performed: `Σ_o N_{o,s,r} h D_{o,s,r}` (feeds token demand `T_t`, AI spend, and rents).

### 4.3 Calibration (§7.3)
BTOS as two series with a wording dummy at 2025-11-17; only `q`, `B*` fitted; sector/size frictions derived; entrant adoption from BTOS young-firm cut.

---

## 5. Layer 4 — Labor-market flows

### 5.1 State
`N_{o,s,r,t}`, `N_{o,r,c,t}`, `M_{j,r,c,t}`, `w_{o,r,t}`, `V_{o,r,t}` as v0.1, plus the price index `P_{r,t}` (§6.2) for real wages.

### 5.2 Labor demand: unified cost–demand treatment

Unit-cost change in sector `s` from both channels (labor cost share `s^L_s` from input-output tables, `[S]`):

$$\Delta \ln c_{s,r,t} = -\,s^L_{s}\Big[\underbrace{\textstyle\sum_o e_{o,s,r}\,\zeta_{o,s,r,t}}_{\text{automation cost saving}} \;+\; \underbrace{\textstyle\sum_o e_{o,s,r}\,\tfrac{\psi\,U_{o,s,r,t}}{1+\psi\,U_{o,s,r,t}}}_{\text{augmentation cost saving}}\Big]$$

Output demand response with pass-through `π_p` (`P.53`) and elasticity `η_s` (`P.60`):

$$\frac{Q_{s,r,t}}{Q^0_{s,r,t}} = \exp\big(-\eta_s\,\pi_p\,\Delta\ln c_{s,r,t}\big)\,(1+\mu_{s,r,t})$$

Labor demand:

$$N^{\ast}_{o,s,r,t} = N^0_{o,s,r,t}\,\frac{Q_{s,r,t}}{Q^0_{s,r,t}}\,\frac{1 - D_{o,s,r,t}}{1 + \psi\,U_{o,s,r,t}}\,(1 + \nu_{o,r,t})$$

Automation and augmentation now enter symmetrically: both cut costs, both raise output demand, and employment falls only where labor saved outruns demand created. At `η = 1` and full pass-through, augmentation is employment-neutral and automation is job-reducing by `D(1 − s^L)` — the Acemoglu–Restrepo displacement-minus-productivity result. `ν` reinstatement as v0.1 (`P.61–P.62`); `μ` demand feedback from §6.

### 5.3 Hiring channel first, layoffs second
Gap `N − N*` is absorbed first by **net occupational attrition**: exits from the occupation (retirement, occupation change, labor-force exit), not total separations. `ς^{occ}` (`P.63`, central 2.5%/quarter, range 1.5–3.5, `[D]` from CPS matched monthly files); job-to-job quits within the occupation are excluded. Remainder by layoffs with friction (`P.64`), EU protection multiplier (`P.33`), seniority protection (`P.65`). Cohort incidence as v0.1; hiring-channel incidence lands on the new-entrant cohort, whose counterfactual wage is the occupation's entry wage `w^{entry}_{o,r}` (`[D]` OEWS 10th percentile).

### 5.4 Transitions
As v0.1 (`P.66–P.72`), with the addition that inflows of displaced workers into a destination occupation add to that occupation's excess supply (§5.5).

### 5.5 Wages, nominal and real

$$\Delta\ln w_{o,r,t} = -\,\varepsilon_w\,\text{XS}_{o,r,t} + \beta\,\psi\,U_{o,r,t} + \Delta\ln w^0_{o,r,t},\qquad \text{XS}_{o,r,t} = \frac{\text{searching}_{o,r,t} + \text{inflow}_{o,r,t}}{N_{o,r,t}}$$

`ε_w` is a quarterly partial adjustment toward the Lichter–Peichl–Siegloch long-run elasticity (`P.73`). **Real wage** `w/P_{r,t}` with the regional price index from §6.2 is what every view reports; nominal is available in the explain trace.

### 5.6 New entrants, demographics, aging
Entrants by cohort from population projections; immigration lever; **aging transitions** per §1.4 applied to every stock each quarter.

### 5.7 AI-production employment
Employment in the AI production sector: `N^{AI}_{r,t} = N^{AI}_{r,2024}·(1 + κ_{DC}·Δcapex^{dom}_{r,t} + κ_{dev}·ΔAIspend_{r,t})` with jobs-per-dollar coefficients from BLS industry data (`P.54–P.55`, `[D]`). Construction jobs are temporary (one-year lag then decay); operations and development jobs persist.

---

## 6. Layer 5 — Macro

### 6.1 Task-based output
Output by sector is the demand-determined quantity from §5.2 valued at baseline prices:

$$Y_{r,t} = \sum_s P^0_s\,Q_{s,r,t} \;+\; \Delta I^{AI,dom}_{r,t}$$

Task units are preserved when a task moves from a worker to AI, so displacement does not reduce output; the cost saving raises TFP:

$$\Delta\ln\text{TFP}_{r,t} = -\sum_s \omega^Y_{s}\,\Delta\ln c_{s,r,t}$$

which is Acemoglu's formula extended to augmentation, and reproduces his upper bound under his assumptions (test in §7.5). Productivity J-curve lag (`P.84`) delays realized `ζ` and `ψ`.

**Incremental AI investment** `ΔI^{AI,dom} = share_dom·(capex_t − capex^{trend}_t)·(1 − co)` where `capex^{trend}` is the investment path already in the baseline and `co` is crowding-out (`P.56`, `E`, central 0.3). Capex path: 2025 anchor and 2026 guidance (`P.80–P.81`), post-2026 growth and plateau (`P.82`), domestic share (`P.83`).

### 6.2 Prices and real income
Regional consumer price index falls with pass-through of sector cost declines weighted by consumption shares (`[S]` CPI weights):

$$\Delta\ln P_{r,t} = \pi_p \sum_s \omega^C_{s}\,\Delta\ln c_{s,r,t}$$

Real wages, real disposable income, and real transfers use `P_{r,t}`. `π_p` is a lever (`P.53`, central 0.7, range 0.3–1.0, `E`) because pass-through is the disputed step between productivity and living standards.

### 6.3 AI spend, rents by value chain, wage share
AI spend by region `X_{r,t} = Σ κ × AI task-units`. Split into stages by cost structure (`P.85`, `[D]` from public gross margins: model providers, cloud, NVIDIA/TSMC/ASML, integration services):

| Stage | Share of spend (central) | Allocated to region of |
|---|---|---|
| Model provider margin | 0.25 | actor home region by market share `m_{a,r,t}` |
| Compute / cloud operations | 0.35 | data-center location (US default; EU data-localization lever shifts EU share) |
| Chips and equipment | 0.25 | US (design) 0.55, TW (fab) 0.35, NL/EU (equipment) 0.10 |
| Integration services | 0.15 | adopting region |

Rents by region are therefore an **output**: they move with prices, market shares, localization, and shocks. Profits `Π = Y − W − δK − X + rents received`. Wage share `W/Y` is no longer mechanically reduced by capex, since only incremental investment enters `Y` and AI-production wages enter `W`.

### 6.4 Households, demand feedback
As v0.1: MPC by decile (`P.86`), multiplier `m` (`P.87`), tradable demand via import shares (`P.88`). Capital income by wealth decile from the Survey of Consumer Finances (`[S]`) distributes profits and rents to households.

### 6.5 Government and financing
Taxes as v0.1 (`[S]`). **Every policy lever carries a financing rule** `{deficit, ai_tax, income_tax_surcharge}`; default `ai_tax` for UBI and wage insurance, `deficit` for retraining. Financed policies reduce disposable income of the financing base, so their net demand effect is shown, not assumed. Fiscal balance reported.

### 6.6 Inequality
Two measures, both reported: **earnings Gini** (labor income, 160-cohort distribution with within-cell spread `P.89`) and **income Gini** (labor + capital income + transfers − taxes, capital income by SCF wealth decile), plus wage share, 90/10, and rents captured by the top decile.

---

## 7. Uncertainty, calibration, and validation

### 7.1 Parametric Monte Carlo with correlated draws
Every `P.xx` with a range is a distribution (triangular unless a standard error is given). Draws are Latin-hypercube through a **Gaussian copula with block correlations** (`P.90`), because independent draws let sector- and class-level errors cancel in aggregates and produce bands that are too narrow:

| Block | Members | Correlation (central) |
|---|---|---|
| Feasibility level | `a_base` across E-classes, `Δ` across classes, `g_m` across modalities | 0.7 |
| Speed | `τ_0`, `ρ` (negative), `γ_n` | ±0.5 |
| Friction | `φ_s` across sectors, `φ_f` across sizes, `I_s` | 0.6 |
| Labor institutions | `ε_w`, `β`, `ℓ`, `ς^{occ}` | 0.4 |
| Regions | same parameter across regions | 0.8 |

`n = 200` draws, seeded; percentiles 10/25/50/75/90 stored per series.

### 7.2 Structural ensemble (mechanism uncertainty)
Parametric draws are conditional on one set of mechanisms. Three disagreements in the literature are **discrete mechanism variants**, run as a `2 × 2 × 2` ensemble by default (25 draws per cell):

| Axis | Variant A | Variant B |
|---|---|---|
| Demand response | Bessen sector elasticities (`η_s` central) | Unit-elastic everywhere (`η_s = 1`) |
| Reinstatement | Acemoglu-low (`ρ_new = 0.15`) | Historical (`ρ_new = 0.6`) |
| Pass-through | Low to wages and prices (`β = 0.15`, `π_p = 0.4`) | Mid (`β = 0.4`, `π_p = 0.8`) |

Bands shown in the UI are the pooled ensemble; the explain endpoint reports parametric and structural spread separately.

### 7.3 Confidence classification
An effect is **high confidence** if its sign holds in every mechanism cell and in ≥ 90% of draws within each cell, and no single parameter flips it within its range (tornado of the top 15 parameters, 30 extra central runs). **Medium**: sign holds in all cells, ≥ 70% of draws. **Low**: otherwise, with the cell or parameter that flips it named.

### 7.4 Calibration targets: what is fitted, what is checked, what is prior-driven

| Target | Data | Fits | Status |
|---|---|---|---|
| Frontier capability clock | METR horizons, Epoch ECI | `C_0`, `τ_0` | fitted |
| Price decline at fixed capability | Epoch price series | `ρ`, `P.06` | fitted |
| Task feasibility points `θ_k` | Anthropic Economic Index task usage by release (2025–26) | `θ_k` for observed tasks | **anchored** (usage is a lower bound on feasibility; single vendor; flagged) |
| Firm adoption path, national | Census BTOS, two wordings, dummy at 2025-11-17 | `q`, `B*_f` only (`p`, `b`, `q^×` fixed at priors) | fitted; identification stated |
| Adoption by sector and size | BTOS sector/size cuts | `φ_s`, `φ_f` | derived |
| Entrant adoption | BTOS young-firm cut, BDS entry rates | `A^{ent}`, `ε` | derived |
| Task-family usage mix | AEI | `ι` composition, `σ` | checked |
| **Canaries test** | Brynjolfsson et al. Aug 2026 (ADP), CPS | hiring-channel share, `ς^{occ}` | **checked with a defined metric** (§7.5) |
| Occupation employment 2023–26 | OEWS, CPS | — | not fitted; shown |
| EU adoption | Eurostat ICT usage in enterprises | `q` for EU | fitted |
| Asia adoption | national surveys where they exist | — | priors only, flagged |

### 7.5 Validation tests (run in continuous integration)
1. **Canaries**: for the top exposure quintile of occupations, the model's 2022Q4–2026Q2 relative employment change of the 22–25 cohort versus the 35–49 cohort must lie within ±5 pp of the observed −19%, **while** aggregate employment in those occupations stays within ±2% of observed. A model that gets the young-worker gap by shrinking the whole occupation fails.
2. **Quiet aggregate**: U.S. aggregate employment effect over 2024–2026 within ±0.3 pp of zero.
3. **Preset replication**: the Acemoglu preset yields TFP ≤ 0.66% and GDP ≈ 1% over ten years within ±0.15 pp; the Goldman preset yields global GDP +7% ± 1.5 pp over ten years. These are tests, not sentences.
4. **Accounting identities**: `Σ_s N_{o,s,r} = Σ_c N_{o,r,c}` each quarter; cohort populations match projections; task units conserved under displacement; fiscal identities close.
5. **Determinism**: same scenario hash and seed give bit-identical output.

### 7.6 Baseline construction
The frozen-AI baseline uses BLS Employment Projections 2024–34 with the occupations BLS documents as adjusted for AI restored to their 2014–2024 trend (`[D]`; the list is in the data inventory), so the counterfactual does not already contain AI. Where BLS documentation is insufficient, the adjustment is flagged and a lever selects trend versus projection.

---

## 8. Scenarios, levers, shocks

### 8.1 Scenario file
Versioned JSON (`scenarios/schema.json`). **Inheritance semantics**: scalar and object fields deep-merge over `parent`; `shocks` are keyed by `id`, a child shock with the same `id` replaces the parent's, `remove_shocks` lists parent shock ids to drop; `overrides` merge by parameter id. Canonicalization resolves inheritance and sorts keys; diffs are computed on canonical form.

```json
{
  "schema_version": "0.2",
  "id": "eu-delay-deepseek-2027",
  "name": "EU AI Act delayed 2y + DeepSeek open frontier 2027",
  "parent": "baseline",
  "levers": {
    "regulation": { "EU": { "ai_act": "delayed_2y" } }
  },
  "shocks": [
    { "id": "deepseek-open-2027", "type": "open_weights_release", "actor": "deepseek", "at": "2027Q1", "frontier_lag_quarters": 0 }
  ],
  "ensemble": { "mechanisms": "all" }
}
```

### 8.2 Levers

| Lever | Parameters | Range exposed |
|---|---|---|
| Capability progress rate (global, per actor) | `P.01`, `P.02`, `λ_a` | doubling 3–12 months; per-actor lag 0–8 q |
| **Ever-automatable mass** (scale on `a_base`) | `P.20–P.22` | 0.5–1.5× |
| **Domain transfer** (non-software progress) | `P.34` | other cognitive 0.4–1.0; interpersonal 0.2–0.8 |
| Cost decline rate; open-weights compression | `P.04–P.06` | 3×–50×/yr; 0.1–0.5 |
| **Compute capacity constraint** | `P.38–P.39`, capex path | on/off; `ξ` 0.5–2 |
| EU AI Act (baseline = Reg. 2026/1744 timetable: Annex III 2 Dec 2027, Annex I 2 Aug 2028) | `P.30–P.32` for EU, by use-case share | {repealed, baseline, delayed_2y, strict_original_2026} |
| **EU data localization** | cloud stage allocation §6.3 | {none, partial, full} |
| U.S. regime (baseline = California SB 53, Colorado SB 26-189 from 2027) | `P.31–P.32` | {none, state_patchwork, federal_light, federal_strict} |
| China licensing (baseline = Interim Measures since 15 Aug 2023) | `P.30`, `V_{a,CN}` | {baseline, tightened, liberalized} |
| Chip export controls (baseline = H200 case-by-case with 25% share, Jan 2026) | `λ_a` CN, `K_t` CN | {rescinded, 2026_status_quo, tightened} |
| Adoption friction by sector, by size; **entrant scale** | `P.48`, `P.49`, `P.52` | 0.5–2× |
| **Pass-through to prices** | `P.53` | 0.3–1.0 |
| Retraining subsidy, wage insurance, UBI, AI tax, shorter week, immigration | as v0.1 | as v0.1, **each with a financing rule** {deficit, ai_tax, income_tax_surcharge} |
| Reinstatement, demand elasticity, wage pass-through (the disagreement axes) | `P.61`, `P.60`, `P.74` | also run as the structural ensemble |
| Capability feedback from revenue | `L.capability_feedback` | off / on |

### 8.3 Shocks
As v0.1 (frontier breakthrough, lab exit, open-weights release, supply-chain cut, recession), each with an `id`. Supply-chain cut now reduces compute capacity `K_t` and tokens-per-dollar `e_τ`, so it raises inference prices through §3.4 rather than through an ad-hoc floor multiplier. Recession sign on adoption remains a lever.

### 8.4 Presets
Acemoglu 2024, Goldman Sachs 2023, IMF 2024, Consensus central. Each preset's headline is a CI test (§7.5).

---

## 9. Explainability

1. **Scenario diff** on canonical form, each entry mapped to mechanism(s).
2. **Channel decomposition**: sequential switch-off in a fixed documented order (automation cost saving, augmentation, demand response, reinstatement, demand feedback, AI investment, policy transfers). Shown by default. **Shapley mode** over the 7 channels (128 central runs) runs as a background job and replaces the sequential attribution when ready; the UI labels which is shown.
3. **Confidence**: §7.3, with parametric and structural spread reported separately.
4. **Trace**: intermediate quantities in the chain (`a`, `θ`, `F`, `Π`, `S`, `A^{max}`, `A`, `D`, `Δln c`, `Q/Q⁰`, `η`, `μ`) for any headline.

The chat layer calls `run`, `compare`, `explain`, `sensitivity`; it never computes.

---

## 10. Parameter registry (v0.2)

IDs stable from v0.1 where the parameter survives; new parameters in new blocks. Tag legend: `S` sourced, `D` derived, `E` estimated by us.

### Capability clock and cost

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.01 | Clock doubling time `τ₀` | 5 | 3–12 | months | S | METR 2025: ~7 mo 2019–25, ~4 mo 2024–25; Time Horizon 1.1: 6.3 mo all-time, 4.3 since 2023, ~3 since 2024 |
| P.02 | Drift in doubling time `γ` | 0 | −0.2–0.3 | per year | E | |
| P.03 | Clock noise sd | 0.15 | 0.05–0.3 | doublings/q | E | |
| P.04 | Price decline at fixed capability `ρ` | 10 | 3–50 | ×/year | S | Epoch AI Mar 2025: 9×–900×/yr across milestones, 40×/yr for GPT-4-level science QA |
| P.05 | Open-frontier lag threshold | 2 | 1–4 | quarters | D | DeepSeek-R1 / Llama-3 episodes |
| P.06 | Open-weights price multiplier | 0.25 | 0.1–0.5 | ratio | D | same |
| P.07 | Tokens per capex dollar improvement `e` | 2 | 1.3–3 | ×/year | E | hardware price-performance (Epoch) |
| P.08 | Base tokens per task-unit `n₀` by modality | by modality | ±50% | tokens | E | AEI conversation lengths |
| P.09 | Integration cost `I_s` | 15 | 5–40 | % annual wage | E | sector-scaled; zero for entrants |
| P.10 | Amortization `H` | 12 | 8–20 | quarters | E | |
| P.15 | Threshold softness `s` | 1.0 | 0.5–2 | doublings | E | |
| P.16 | Substitution share `σ` (initial) | 0.45 | 0.25–0.7 | share | S | AEI automation share 43% (Feb 2025), 49% (Sep 2025), 45% (Jan 2026); by task family |
| P.17 | `σ` drift per doubling | +0.01 | −0.02–0.06 | share | D | not monotone in AEI; range includes zero |
| P.19 | Robotics doubling time | 24 | 12–48 | months | E | |
| P.36 | Clock saturation `C_max` | 20 | 14–24 | doublings | E | beyond this only `a_k` binds |

### Task feasibility (new in v0.2)

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.20 | Ever-automatable `a_base(E1)` | 0.9 | 0.7–1.0 | probability | E | |
| P.21 | `a_base(E2)` | 0.7 | 0.4–0.9 | probability | E | |
| P.22 | `a_base(E0)` | 0.25 | 0.05–0.5 | probability | E | non-zero because labels are GPT-4-era |
| P.23 | Presence exponent `λ_π` | 1.5 | 0.5–3 | — | E | O*NET Work Context presence items |
| P.24 | AEI usage threshold for anchoring `θ` | 0.5 | 0.25–1.0 | × employment share | E | usage is a lower bound on feasibility |
| P.25 | `Δ(E1)` beyond 2026Q2 clock | 1 | 0–3 | doublings | E | |
| P.26 | `Δ(E2)` | 3 | 1–5 | doublings | E | |
| P.27 | `Δ(E0)` | 6 | 3–10 | doublings | E | |
| P.28 | Reliability shift, high-consequence tasks | 1 | 0.5–2 | doublings | D | METR 80% vs 50% horizon ratio |
| P.29 | Token growth per doubling `γ_n` | 0.7 | 0.4–1.0 | log₂ tokens / doubling | E | agentic token use grows with task length |
| P.34 | Domain transfer `g_m` | software 1.0; other cognitive 0.7; interpersonal 0.5 | 0.4–1.0; 0.2–0.8 | — | E | METR measures software tasks only |
| P.35 | Profitability softness `b_κ` | 0.5 | 0.25–1 | log units | E | |
| P.59 | `a_phys` (robotics track) | 0.3 | 0.1–0.6 | probability | E | |

### Regulation and access

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.30 | Availability delay `δ^reg` | EU 1; CN 4 | EU 0–4; CN 2–8 | quarters | S/E | EU launch delays; CN frontier gap (Epoch) |
| P.31 | Compliance premium `χ` **by use-case class** | high-risk EU 10; transparency 1; unregulated 0 | 2–30; 0–3; 0 | % of `κ` | E | no measured value; Annex III scope |
| P.32a | High-risk use-case friction `φ^{HR}` | 0.6 | 0.3–0.9 | multiplier | E | applies to Annex III task share only |
| P.32b | Transparency-class friction `φ^{T}` | 0.9 | 0.7–1.0 | multiplier | E | |
| P.33 | EU employment-protection multiplier on layoffs | 0.5 | 0.3–0.8 | multiplier | D | OECD EPL ratio |
| P.37 | Availability gate `v_min` | 0.5 | 0.25–0.75 | — | E | |

### Compute and supply (new in v0.2)

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.38 | Compute depreciation | 20 | 12–28 | quarters | S | hyperscaler useful-life disclosures (5–6 years) |
| P.39 | Capacity price exponent `ξ` | 1.0 | 0.5–2 | — | E | |
| P.57 | Market-share capability sensitivity `β_m` | 1.0 | 0.5–2 | per doubling | E | |
| P.58 | Market-share price sensitivity `ψ_p` | 0.5 | 0.2–1 | — | E | Ramp vendor shares as loose check |

### Adoption

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.40 | Augmentation gain `ψ` | 0.25 | 0.10–0.50 | share | S | Brynjolfsson–Li–Raymond 14/15%, 34% novices; Noy–Zhang −40% time; Peng 55.8%; Dell'Acqua 12.2% tasks, 25.1% faster |
| P.41 | Bass `p` (fixed, not fitted) | 0.03 | 0.01–0.06 | per year | S | Sultan et al. 1990 |
| P.42 | Bass `q` (fitted) | 0.38 prior | 0.2–0.6 | per year | S→fit | |
| P.43 | Spillover `q^×` (fixed prior) | 0.1 | 0–0.3 | per year | E | not identifiable from shared clock |
| P.44 | Spillover lag `L` | 4 | 2–8 | quarters | E | |
| P.45 | Spillover weights | TiVA-based | — | — | D | |
| P.46 | Hurdle `B*_f` by size (fitted) | — | — | $/worker-q | E→fit | |
| P.47 | Hurdle dispersion `b` (fixed) | — | — | $/worker-q | E | |
| P.48 | Sector friction `φ_s` | from BTOS | ×0.5–2 | multiplier | D | |
| P.49 | Size friction `φ_f` | small 0.6, mid 0.8, large 1.0 | ±0.2 | multiplier | D | BTOS 32% employment- vs 18% firm-weighted |
| P.50 | Intensity ceiling `ι^max` | 0.7 | 0.4–0.9 | share | E | |
| P.51 | Intensity ramp | 0.08 | 0.04–0.15 | per quarter | E | |
| P.52 | Entrant adoption `A^{ent}` and entry rate `ε` | BTOS young firms; BDS ~8%/yr | ±50% | share; per year | D | |

### Labor

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.53 | Pass-through to prices `π_p` | 0.7 | 0.3–1.0 | share | E | the disputed step from productivity to living standards |
| P.54 | Data-center jobs per $bn capex | from BLS/QCEW | ±50% | jobs/$bn | D | construction temporary, operations persistent |
| P.55 | AI-development jobs per $bn AI spend | from BLS OEWS 5415/5182 | ±50% | jobs/$bn | D | |
| P.60 | Output demand elasticity `η_s` | tradables 1.0; local services 0.6 | 0.5–1.5; 0.3–1.0 | elasticity | S | Bessen 2019 |
| P.61 | Reinstatement `ρ_new` | 0.4 | 0.1–0.8 | share | E | ensemble axis |
| P.62 | New-task lag | 8 | 4–16 | quarters | E | |
| P.63 | **Net occupational attrition** `ς^{occ}` | 2.5 | 1.5–3.5 | %/quarter | D | CPS matched files: retirement + occupation change + LF exit; within-occupation quits excluded (JOLTS total separations 3.3%/mo is the wrong quantity) |
| P.64 | Layoff friction | 0.25 | 0.1–0.5 | share of gap/q | E | |
| P.65 | Seniority protection | 0.5 | 0–1 | index | E | |
| P.66 | Skill-distance decay | fitted | — | — | D | |
| P.67 | Occupation transition matrix | — | — | — | D | CPS matched monthly |
| P.68 | Retraining entry base rate | by cohort | ±50% | per quarter | D | |
| P.69 | Scarring `ℓ` | 0.12 | 0.05–0.25 | share | S | Jacobson et al. 1993; Davis–von Wachter 2011 |
| P.70 | Retraining success | 0.55 | 0.35–0.75 | probability | E | WIOA |
| P.71 | Retraining duration | 4 | 2–8 | quarters | D | |
| P.72 | Hours conversion, shorter week | 0.8 | 0.5–1 | share | E | |
| P.73 | Wage adjustment `ε_w` | 0.3 | 0.15–0.6 | per quarter | S | partial adjustment toward Lichter et al. 2015 (mean −0.51, median −0.39) |
| P.74 | Productivity pass-through to wages `β` | 0.3 | 0.1–0.6 | share | E | ensemble axis |

### Macro

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.56 | Crowding-out of incremental AI investment | 0.3 | 0–0.7 | share | E | |
| P.80 | U.S. AI capex 2025 | 400 | 380–415 | $bn | S | Alphabet 91.4, Amazon 131.8, Meta 72.2, Microsoft ≈88–118 |
| P.81 | Capex growth 2026 | 80 | 60–100 | % | S | Jul 2026 guidance ≈ $720–760bn |
| P.82 | Capex path after 2026 | +10%/yr to 2029, then flat | −10–+30%/yr; plateau 2027–2033 | — | E | |
| P.83 | Domestic value-added share of capex | 0.5 | 0.3–0.7 | share | E | |
| P.84 | Productivity J-curve lag | 4 | 0–8 | quarters | S | Brynjolfsson–Rock–Syverson |
| P.85 | Value-chain split of AI spend | model 0.25 / compute 0.35 / chips 0.25 / integration 0.15 | ±0.1 each | share | D | public gross margins (model providers, cloud, NVIDIA, TSMC, ASML) |
| P.86 | MPC by decile | 0.9 → 0.4 | ±0.1 | share | S | Fagereng et al.; CBO |
| P.87 | Demand multiplier `m` | 0.6 | 0.3–1.2 | — | S/E | |
| P.88 | Import shares | TiVA | — | — | S | |
| P.89 | Within-decile spread | CPS | — | — | D | |
| P.90 | Copula block correlations | §7.1 table | ±0.2 | — | E | |

Counts: 77 parameters; 18 `S`, 21 `D`, 38 `E`. The estimated share rose from v0.1 because the fixes replaced hidden assumptions with named parameters. Every `E` is a lever.

---

## 11. Outputs

| Output | Dimensions | Feeds view |
|---|---|---|
| Employment `N` vs `N⁰`; AI-production employment | o, s, r, g, c, t | map, heatmap, cohort, Sankey |
| Ever-automatable share `Σ w a`, realized `D` | o, r, t | heatmap (x = automatable share, y = realized) |
| Labor-state flows, with aging | j→j', r, c, t | Sankey, cohort |
| Nominal and **real** wages, wage share, earnings Gini, **income Gini**, 90/10 | o, r, c, t | cohort, dashboard |
| Output, TFP, price index, profits, **rents by value-chain stage and region** | r, v, t | dashboard, compare |
| Tax base, transfers, **financing**, fiscal balance | r, t | dashboard |
| Adoption ceiling and realized adoption, intensity, token demand vs capacity | s, f, r, t | timeline, explain |
| Clock, regional capability, prices, market shares, releases, regulatory events | a, r, t | supply timeline |
| Channel decomposition, tornado, **parametric vs structural spread** | per series | explain, insight, compare |

---

## 12. Known limitations (v0.2)

1. **Still no market clearing.** Prices now fall with costs and wages adjust partially, but nothing clears; tail scenarios (> 15% displacement in a decade) carry a validity warning.
2. **`a_k` and `θ_k` are the largest estimates.** The ever-automatable mass replaces v0.1's threshold scale problem with an explicit, arguable prior; the usage anchoring is single-vendor and treats usage as a lower bound on feasibility.
3. **Domain transfer `g_m` has no measurement.** It is the honest statement that METR's series is about software.
4. Cohort tracking at occupation level, not occupation × sector.
5. O*NET is U.S.-centric; crosswalk quality scored and shown.
6. China occupational data is thin; interpolated between census years and flagged.
7. Informal sector outside the model.
8. No financial sector, debt dynamics, or monetary policy; policy financing is a static rule.
9. Actor economics beyond public data are not modelled.
10. Robotics is a single slow clock.
11. No migration between sub-regions.
12. Compute capacity is a single global stock with regional access; no data-center siting model beyond the localization lever.

---

## 13. Questions for the reviewer

1. **Capability units in the UI**: horizon units ("AI can do 8-hour tasks") or an abstract level? Recommendation: horizon units.
2. **Ever-automatable defaults** (`P.20–P.22`): 0.9 / 0.7 / 0.25 are our priors. If you have a view on the E0 mass in particular, it moves the 2040 ceiling directly.
3. **Recession shock sign on adoption**: lever with default neutral.
4. **U.S. state resolution in Phase 1**: recommend yes.
5. **Presets first-class in compare**: recommend yes.
6. **Structural ensemble on by default** costs nothing at 200 draws but makes every band wider. Recommend yes; the alternative is a "central mechanisms" toggle that a demo audience will misread as confidence.

---

## 14. Phase mapping

| Phase | Spec sections implemented | Regions | Draws |
|---|---|---|---|
| 1 | §1–3 (excl. 1.4), §3.2–3.4 (US), §4, §5.2–5.5, §5.7, §6.1–6.2, §7.5–7.6 | US national + states | central only |
| 2 | §1.4, §5.6 (cohorts, aging), §7.1–7.4, §8, §9, presets with CI tests | US | 200 (8-cell ensemble) |
| 3 | §3.1, §3.3, §3.6, §4 spillover and entrants, §5.7, §6.3–6.6 | all | 200 |
| 4 | chat over §9 | all | 200 |
| 5 | methodology write-up | all | 200 |

---

## 15. Change log: v0.1 adversarial review → v0.2

| # | Review finding | Change | Where |
|---|---|---|---|
| 1 | Thresholds on the horizon scale made every non-physical task feasible by 2028 | Split into ever-automatable mass `a_k`, usage-anchored feasibility point `θ_k`, domain transfer `g_m`, clock saturation; presence flag from O*NET Work Context; exposure axis = `Σ w a` | §2.2–2.3, P.20–P.29, P.34, P.36 |
| 2 | Automation lowered GDP | Task-based output: task units conserved; output is demand-determined from unit costs; TFP = cost saving | §6.1 |
| 3 | Demand response applied only to augmentation | Unified unit-cost equation; both channels raise output demand via `η_s`; labor cost share `s^L` applied | §5.2 |
| 4 | Wage share and rent split were inputs | Only incremental investment enters `Y`; AI-production wages enter `W`; rents allocated by value-chain stage, endogenous market shares, localization lever; Taiwan/NL included | §6.3, §3.6, P.85 |
| 5 | Cohorts never aged | Quarterly aging transitions; deciles re-ranked annually | §1.4, §5.6 |
| 6 | Feasible treated as profitable | Task-level profitability test `Π_k`; `S` uses profitable-feasible share; cost-saving share `ζ` | §2.4 |
| 7 | Attrition channel used total separations | Net occupational attrition 2.5%/q from CPS matched files | §5.3, P.63 |
| 8 | Adoption speed and ceiling conflated | Benefit-driven ceiling `A^{max}`; friction on speed only | §4.2 |
| 9 | Availability multiplied a log index | Availability gates the actor set and adoption | §3.3 |
| 10 | Cost layer collapsed; static tokens per task | Tokens grow with feasibility point; compute capacity constraint with price multiplier; capex linked to token demand | §2.2, §3.4, P.29, P.38–P.39 |
| 11 | No price level; nominal wages | Regional price index from cost pass-through; real wages reported | §6.2, §5.5, P.53 |
| 12 | EU AI Act applied by sector | Use-case classes from Annex III mapped to task families; friction and premium apply to that task share only | §2.2, §4.2, P.31–P.32 |
| 13 | Capex not incremental; policies unfinanced | Incremental over baseline with crowding-out; financing rule per policy lever | §6.1, §6.5, P.56 |
| 14 | Bass parameters unidentified | `p`, `b`, `q^×` fixed at priors; `q`, `B*_f` fitted; wording dummy | §4.3, §7.4 |
| 15 | Independent draws narrow the bands | Gaussian copula with block correlations | §7.1, P.90 |
| 16 | Parametric ≠ structural uncertainty | 2×2×2 mechanism ensemble by default; confidence requires sign stability across cells | §7.2–7.3 |
| 17 | Replication claims untested | Preset replication as CI tests with tolerances | §7.5 |
| 18 | Baseline already contains AI | BLS AI-adjusted occupations restored to trend; lever | §7.6 |
| 19 | Earnings Gini missed capital income | Income Gini with SCF wealth-decile capital income; rents to top decile reported | §6.4, §6.6 |
| 20 | State occupation × industry does not exist | IPF construction stated and flagged | §1.3 |
| 21 | Shock inheritance undefined | Shocks keyed by id; replace/remove semantics | §8.1 |
| 22 | Shapley breaks runtime budget | Sequential by default; Shapley as background job | §9 |
| 23 | Spillover not identifiable | `q^×` fixed prior | §4.2 |
| 24 | AI industry employment absent | AI-production sector driven by capex and spend | §1.2, §5.7 |
| 25 | AI-native entrants missing | Entry term with zero integration cost | §4.2, P.52 |
| 26 | Canaries check undefined | Metric with tolerance and the aggregate-flat condition | §7.5 |

---

## 16. Implementation notes and deviations (Phase 1–2 build)

Where the code departs from or sharpens the text above, the code is documented here so the two do not drift.

| Topic | Spec text | Implementation | Why |
|---|---|---|---|
| Wage rule (§5.5) | partial adjustment toward the long-run Lichter et al. elasticity | partial adjustment (speed `P.73`) toward a **wage-curve target** `−0.1·ln(1 + XS/0.04) + β·ψ·U` (Blanchflower–Oswald elasticity −0.1, S; 4% baseline unemployment, E) | the v0.2 text had no mean reversion; a persistent excess supply drove wages down without bound in the first run |
| Demand feedback (§6.3) | consumption from disposable income by cohort with MPC by decile | Phase 1–2: `ΔC = 0.7·ΔW + 0.4·ΔΠ` with `ΔΠ = ΔY − ΔW`; consumption = 0.68·Y⁰; decile MPCs arrive with the cohort income layer in Phase 3 | counting lost wages without the offsetting profits produced a doom loop |
| Task resolution (§1, §2) | ~120 occupation clusters | all 831 six-digit occupations; tasks merged into ~9,400 *task groups* (identical label, modality, use case, consequence, presence bucket within an occupation); 450 clusters carried as ids for aggregation | exact for every equation except the E1 fallback spread; 200 draws run in ~9 s on 4 cores |
| Monte Carlo (§7.1) | draws around registry centrals | draws are **re-centred on the scenario's current value** of each parameter (levers and overrides applied), range widened to include it | otherwise a lever would move the central run but not the band |
| Structural ensemble (§7.2) | 2×2×2 cells, 25 draws each | draw 0 is the pure central run (cell "central"); draws 1..199 rotate through the 8 cells | the central line must be the scenario as specified, not one cell's variant |
| Feasibility anchoring (§2.2) | AEI task usage anchors `θ` for observed tasks | AEI unavailable offline; E1 tasks spread over 2024–2025 by a deterministic hash, E2/E0 by class offsets; `meta.data_flags.aei_anchoring = "unavailable"` | replaced when `ingest/aei.py` runs |
| Cohorts (§1.4) | joint from CPS ASEC by IPF | product of marginals: age FIXTURE (national distribution tilted by Job Zone), education E (Job Zone), decile D (OEWS percentiles); cohort effects tracked as *jobs below baseline* by cohort with aging, re-employment and exit hazards by age (E) | CPS microdata needs IPUMS access; `ingest/cps_asec.py` fits the joint |
| Compute capacity (§3.4) | capacity from capex, price multiplier when demand exceeds it | implemented; never binds in the central run (multiplier 1.0) | token demand from 8% of task-hours is small against a $700bn/yr capex path |
| Tornado (§7.2) | top 15 of all parameters | one-at-a-time low/high for a curated 20 parameters (41 batched draws, ~4 s) | runtime |
| Retraining (§5.4) | entry, duration, success | implemented as a duration queue; failures return to searching | — |
| Layoff channel (§5.3) | attrition first, layoffs second | at the central pace attrition absorbs the whole gap, so layoffs are zero in the baseline; the layoff path activates in fast-clock scenarios | a finding, not a bug (`docs/findings-phase1.md`) |

## References (parameter sources)

- Acemoglu, D. (2024). *The Simple Macroeconomics of AI.* NBER WP 32487; *Economic Policy* 40(121).
- Acemoglu, D., Restrepo, P. (2019). Automation and New Tasks. *JEP* 33(2).
- Anthropic (2025–26). *Anthropic Economic Index* reports (Feb, Mar, Sep 2025; Jan, Mar, Jun 2026) and dataset (CC BY).
- Autor, D., Chin, C., Salomons, A., Seegmiller, B. (2024). New Frontiers. *QJE* 139(3).
- Bessen, J. (2019). Automation and Jobs. *Economic Policy*.
- Brynjolfsson, E., Chandar, B., Chen, R. (2025; rev. Aug 2026). Canaries in the Coal Mine? Stanford Digital Economy Lab.
- Brynjolfsson, E., Li, D., Raymond, L. (2023; *QJE* 2025). Generative AI at Work.
- Brynjolfsson, E., Rock, D., Syverson, C. (2021). The Productivity J-Curve. *AEJ: Macro*.
- Cazzaniga, M. et al. (2024). Gen-AI and the Future of Work. IMF SDN/2024/001.
- Davis, S., von Wachter, T. (2011). Recessions and the Costs of Job Loss. *BPEA*.
- Dell'Acqua, F. et al. (2023). Navigating the Jagged Technological Frontier. HBS WP 24-013.
- Eloundou, T., Manning, S., Mishkin, P., Rock, D. (2024). GPTs are GPTs. *Science*.
- Epoch AI (2024–26). Notable AI Models; Epoch Capabilities Index; LLM inference price trends.
- Felten, E., Raj, M., Seamans, R. (2021). *SMJ* 42(12).
- Federal Reserve Board. Survey of Consumer Finances (2022).
- Gmyrek, P. et al. (2023; 2025). Generative AI and jobs. ILO WP 96, WP 140.
- Goldman Sachs (2023). The Potentially Large Effects of AI on Economic Growth.
- Jacobson, L., LaLonde, R., Sullivan, D. (1993). *AER*.
- Kwa, T. et al. (2025). Measuring AI Ability to Complete Long Tasks. METR; METR (2026) Time Horizon 1.1.
- Lichter, A., Peichl, A., Siegloch, S. (2015). *European Economic Review* 80.
- Noy, S., Zhang, W. (2023). *Science* 381.
- Peng, S. et al. (2023). GitHub Copilot productivity.
- Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744 (Digital Omnibus on AI).
- Sultan, F., Farley, J., Lehmann, D. (1990). *JMR* 27(1).
- U.S. Census Bureau. BTOS AI question (2023–); Business Dynamics Statistics.
- U.S. BEA. Input-Output accounts (labor cost shares). U.S. BLS. OEWS, CPS, JOLTS, CPI relative importance, Employment Projections 2024–34 and methodology notes on AI adjustments.
