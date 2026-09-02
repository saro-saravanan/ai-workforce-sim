# Findings so far — Phase 8 (the story layer, policy wiring, the Seba/RethinkX preset)

Branch `spec/model-v0.3` at Phase 8. Baseline, U.S., 256 draws, 32 structural cells; companions (four policy runs and the Seba preset) at 64 draws, central run quoted. Everything is a difference from a world in which AI stopped improving in 2023.

![Story view](screenshots/phase8-story-light.png)

## 1. One set of numbers

The reports of Phases 1–7 gave the same fact three ways (jobs below baseline, workers displaced, unemployed) and readers added them up. The story layer keeps two ledgers and explains why they differ:

- **Jobs ledger (positions).** About 9.5 million fewer jobs exist in 2040 than there would have been, on a base of 169 million: one job in eighteen. Likely range 18 million fewer to no loss. The biggest remover is software doing tasks (13.4 million by channel accounting); the biggest offset is cheaper output selling more (5.7 million).
- **People ledger (who was affected).** Over the period 11.7 million people found the job they had, or would have had, gone: 10.4 million positions never offered to new entrants, 0.7 million layoffs, 0.5 million full-time equivalents of gig and freelance hours cut. Of them 9.4 million found other work, 1.3 million left the workforce and 0.2 million are unemployed in 2040. Unemployment peaks at +450,000 in 2037.

The ledgers do not add up to each other because a person who finds other work fills a position someone else would have had. Saying so once, in the header of every story, removed the most common misreading of the earlier reports.

## 2. The seven findings and how sure the model is

| # | Finding | Sureness |
|---|---|---|
| 1 | More jobs than today, fewer than there would have been (9.5 million by 2040) | leaning this way |
| 2 | People are not fired, they are not hired (10.4 million unfilled entries vs 0.7 million layoffs) | we would bet on it |
| 3 | The young pay first (under-25s carry 42% of the shortfall, 5% of their jobs; over-55s almost nothing; no degree loses three times a graduate) | leaning this way |
| 4 | Pay up 4%, the economy up 8%, the workers' share of income down 4.8 points | we would bet on it |
| 5 | Three waves: office work now (graphic designers −17% by 2030), robots and vehicles later (0.2% of task-hours in 2030, 6.9% in 2040), AI-made content category by category (translation and voice 72% of spending by 2040, video 8%) | leaning this way |
| 6 | The money flows to the U.S. and the chip makers ($151 billion a year of AI income to the U.S., $50 billion to China; largest GDP gains in Taiwan and Korea) | leaning this way |
| 7 | Two futures, and the difference is partly a choice: gains spent back (+13%, 22 million more jobs) or pocketed (−6%) | a coin flip |

Sureness is the existing confidence classification renamed for readers: high → "we would bet on it", medium → "leaning this way", low → "a coin flip". No finding was reworded to sound surer than its classification.

## 3. Tony Seba as a predictor: what the model can and cannot reproduce

The Seba/RethinkX preset transcribes his framework into levers rather than asserting his numbers: electronics-like learning rate (0.25), fleets built at the fastest historical ramp (1.5/yr), 1.5× utilization (transport as a service), unit price 0.7×, embodiment clocks doubling every 8–12 months and coupled to the software frontier, accelerated approvals where fleets already operate, eroding preference for human-made content.

- **Robotaxis.** Under the preset robotaxis pass 10% of taxi and ride-hail driver work in 2030Q4 and reach 76% by 2035, then stop: approval paths cap coverage at 85% and the ever-automatable share of the role at 85%. The baseline reaches 10% only in 2037. Trucking and last-mile delivery follow the same shape (83% by 2035 under the preset).
- **What made this possible.** Task-level substitution had left 69% of a taxi driver's job in place with a vehicle that carries the passenger, because the task engine discounts tasks that need a person present. Phase 8 introduces a whole-job rule for driving roles: the presence discount is lifted for their driving tasks and realized displacement is scaled by the inverse driving weight, so a fully covered fleet removes the role. `meta.whole_job` reports the numbers behind the rule for each role.
- **Scoreboard verdicts.** Against Seba's 2017 claim of 95% of passenger miles autonomous by 2030 the model reads 12% coverage in 2030 under his own assumptions ("model lower"); against 90% driver displacement, 11% in 2030 and 76% by 2035. Against RethinkX 2020's 20% of physical work disrupted by 2030, the model reads 8.9% of task-hours by 2035. The model agrees with the *shape* (an S-curve that goes from 1% to 75% in seven years) and disagrees on the *date* by about five years, and the disagreement is not about cost: at half the unit price the curve does not move. It is about approvals, the production ramp, and the multi-region fleet allocation (U.S.-only runs reach 73% by 2030; the global ramp shared across ten regions delays the U.S. curve).
- **Whole economy.** The preset moves 2040 employment from −5.6% to −7.2% (central) and GDP from +8.1% to +10.0%. Robots and vehicles do 8.9% of task-hours by 2035 against 6.9% by 2040 in the baseline.

The preset is labelled as levers, and the 2017 and 2020 forecast rows are transcribed from recollection (`source_tag` V?) until the reports are fetched and cited (`docs/data-inventory.md`).

### 3b. Seba's 2024–2026 claims: humanoids and transport-as-a-service

RethinkX's current labour work (*Near-zero cost labor*, 2025; *This time, we are the horses*, updated December 2025; *The Painful Truth about AI & Robotics*, 2026) and the 2026 *Rethinking Energy, Mobility, and Materials* roadmap make bigger claims than the 2017 transport report: humanoid labour under $10/hour at entry and under $1/hour before 2035, robots doing as much work as people by the late 2030s, and TaaS carrying over 80% of urban passenger miles by about 2035. A second preset, `preset-seba-2026`, pushes the manipulation class as hard as the first pushes driving (every clock at six months, the ever-automatable share of manipulation at the top of its range, utilization ×1.6, unit price ×0.5, accelerated approval everywhere, induced demand ×2), and five scoreboard rows test the claims. Companions at 64 draws, central run:

| Claim | Baseline | Seba 2017 preset | Seba 2026 preset |
|---|---|---|---|
| Humanoid labour under $10/hour at entry (2025) | $4.27, model lower | $1.38 | $0.92 |
| Under $1/hour before 2035 (2034) | $2.03, within band | $0.06 | $0.04 |
| Robots do half of physical work by 2039 | 9%, model lower | 38%, model lower | 48%, model lower (by 1.5 points) |
| TaaS 50% of urban passenger miles by 2032 (robotaxi coverage) | 3%, model lower | 71%, within band | 71%, within band |
| TaaS over 80% by 2035 | 8%, model lower | 85%, within band | 85%, within band |

Three readings.

- **Cost is not where the model disagrees with him.** The model's hardware cost per worker-hour for manipulation (annualized unit price over utilized hours, integration excluded) is below RethinkX's entry figure even in the baseline, and under either preset it falls to a few cents by the mid-2030s. What holds embodied displacement to 11% of all task-hours under the 2026 preset is the production ramp, approval, and the ceiling on how much of physical work can ever be automated, not the price of the robot.
- **"As much labour as humans" is a claim about physical work.** Embodied channels are 24% of all task-hours in the model's task partition; office and analytical work is the software channel. Measured against physical task-hours, the 2026 preset reaches 48% by 2039 against the claim of 50%, so the model can essentially reproduce his humanoid claim when every constraint is set to its most favourable value. It cannot reproduce it at central assumptions (9%), and the difference is the ramp cap (1.5/yr against 0.5/yr) and the ever-automatable share (0.85 against 0.6) more than anything else.
- **TaaS by 2035 is within reach of the model under his assumptions but capped by approval.** Robotaxi coverage saturates at 85% because the accelerated approval path stops there; the 2032 and 2035 TaaS rows read within band under either preset, and the 2017 "95% by 2030" row still reads model lower because the fleet does not exist in 2030 (coverage 12%) whatever the cost.

The 2026 preset costs 2.8 points of 2040 employment against the baseline (−8.4% against −5.6%) and adds 2.8 points of GDP (+10.9%). The two Seba presets are both named futures in the story. The forecast rows for the labour series come from page summaries and the user-supplied summary of the 2026 report; `source_tag` says so on each row, and `docs/data-inventory.md` lists what to fetch to confirm them.

## 4. What could be done: the policy runs

| Policy | Jobs vs baseline, 2040 | Unemployed | Pay per head | Cost | Validity |
|---|---|---|---|---|---|
| Retraining subsidy, 50% of wage | no measurable change | −37,000 | — | $5 bn/yr, deficit | ok |
| Wage insurance, 50% for two years | no measurable change | — | — | $3 bn/yr, AI tax | ok |
| $500/month basic income, 30% AI tax | +13.8 million | +70,000 | — | $1,742 bn/yr, of which $1,721 bn deficit (5% of GDP) | **outside the model's range** |
| 36-hour standard week | +17.9 million heads | — | −10.5 points | none | ok, but heads not hours |

Two lessons. Targeted labour-market policies barely move the headline because the headline is set by labour demand, not by frictions; they move who bears it. Large transfers move the headline a lot in a model with no inflation, interest-rate or debt response, and the run says so in every sentence it applies to. The work-week result is arithmetic: the same hours over more heads.

## 5. Your outlook

![Your outlook](screenshots/phase8-outlook-light.png)

`GET /api/outlook/{hash}?occ=&age=` gives one occupation and one age band a verdict (rank among all occupations), the 2030 and 2040 numbers with their range, whether the automated task-hours are software or machines, pay for those who stay, and nearby occupations that grow. Taxi drivers under the baseline: among the hardest hit, 32% fewer jobs by 2040 (1% by 2030), mostly machines and vehicles. Customer service representatives: about average, 8% fewer, mostly software. Static mode computes this client-side from the run document with the same rules.

## 6. What I do not trust yet

- The whole-job rule assumes the non-driving tasks (loading, assisting passengers, paperwork) vanish with the role. Risk #37.
- The policy wiring is a first pass (risk #36); the UBI result is a demonstration of the validity flag, not a finding.
- The "gains spent back" future is the tornado extreme of one parameter (P.87) and reads as a very rosy world; it is the upper edge of the model's range, not a scenario anyone has argued for.
- Regional job numbers outside the U.S. still rest on placeholder occupation mixes, so "largest job losses in the UK and EU" is a structure statement, not a measurement.
- Eight of twelve scoreboard rows compare a claim with the nearest model quantity (`proxy = 1`), and their verdicts are about direction and size. For the two cost rows, "model lower" means the model is the more aggressive of the two.
- The manipulation cost per hour is hardware only; integration (P.09) and the human-presence discount are applied inside the profitability test, so the scoreboard's cost figure understates what an employer pays.

## 7. Runtime and verification

Baseline 57 s at 256 draws (Monte Carlo 33 s, tornado 12 s, channels 6 s); companions about 45 s each at 64 draws on first use, cached by hash after. Tests: `sim/tests/test_phase8.py` (policy off in baseline, work week converts hours to heads, UBI trips the fiscal flag, retraining raises retraining and lowers unemployment, whole-job rule tracks coverage, induced demand softens embodied job loss, scoreboard verdicts and preset movement), `api/tests/test_story.py` (beats, reconciled numbers, companions, outlook, executive brief formats and endpoints), plus the Phase 6–7 application tests.
