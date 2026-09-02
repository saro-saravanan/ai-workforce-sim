# Findings so far — Phase 6 (embodied channels: robotaxis, trucks, robots)

*Phase 6 implements the embodied part of specification amendment v0.3 (`docs/model-spec-v0.3-applications.md`): one channel per task group, four embodiment classes with hardware unit economics, production ramps, approval paths and deployment coverage, a self-employed and platform workforce stock, and a catalogue of ten embodied applications. Numbers are the 256-draw, ten-region, 16-cell baseline. Every embodied parameter is an authors' estimate marked V? in the amendment; read the numbers as the consequences of those estimates, not as forecasts.*

## 1. What changed in the headline

| U.S., 2040 Q4, median [10–90] | v0.2 (Phase 5) | v0.3 Phase 6 |
|---|---|---|
| Employment vs frozen-AI baseline | −2.5% [−6.5, +1.2] | −4.8% [−9.7, +0.5] |
| GDP | +6.8% [+4.1, +12.6] | +8.1% [+4.7, +16.3] |
| Real wages | +3.1% [+1.9, +6.5] | +3.8% [+1.7, +7.2] |
| Wage share | −3.5 pp | −4.6 pp [−6.2, −3.1] |
| Sign confidence, employment | low | medium |

Two things moved the headline. The **embodied channel** contributes −2.1 pp to 2040 employment at the central draw (the channel bar sits between augmentation and demand response), and the **headline denominator** now counts FTE including 11.6 M self-employed and platform workers in the U.S., which puts rideshare drivers and freelance workers inside the model for the first time. The sign of the employment effect is now medium rather than low confidence: adding a channel that only ever pushes employment down raises the share of draws that agree on the sign, which is arithmetic, not insight.

The **central draw sits well below the median** for the embodied share (2.1% of task-hours against a median of 5.4%). The hardware learning rate is a structural axis at 0.08 and 0.20 while the central value is 0.12, and the ramp cap's range (0.3–1.5 per year) is one-sided around its central 0.5, so the median draw is faster than the specified scenario. This is the documented "range widens to include the lever" behaviour and the reason the dashed central line and the shaded band should be read together.

## 2. Three findings from the embodied layer

1. **Embodied automation is late, then large, and the ramp is the gate.** Robotaxis reach 1% displacement of their target occupations in 2035 and 7% by 2040; autonomous trucking reaches 10% of heavy-truck driving by 2040; warehouse robotics 4%. At the central draw the driving clock saturates by 2030 and the manipulation clock by 2032, so capability is not what holds these back. Production capacity is: the ramp cap (P.117) is the fifth-largest employment sensitivity in the whole model (3.4 pp swing), ahead of every feasibility parameter except the demand multiplier's neighbours. This is exactly attack 4 of the pre-review, and the tornado now makes it visible rather than smuggled in.
2. **At central unit economics, mobile manipulators are cheaper than any wage anywhere by the mid-2030s.** A unit priced at $70k in 2025 falls to about $21k by 2040 on the learning curve, and at 60% utilization and 0.7 task-units per hour costs about $1.30 per worker-hour equivalent. The profitability test then binds nowhere, including India, and the only remaining gates are the feasibility clock, the ramp, and the ever-automatable mass of 0.6 with the presence penalty. The consequence is fleets of 4.5 M manipulators in the U.S., 6.5 M in the EU and 25 M in China by 2040 in the median draw. Whether that is a forecast or an artefact depends on three V? numbers: unit price, utilization, and task-units per hour for unstructured work. Their ranges span a factor of five in cost, the ranking of the learning-rate axis in the structural spread (8.6 pp, up from 6.1) shows how much rides on them, and they are now the first verification items in the data plan.
3. **The self-employed margin behaves differently, and the cohort picture holds.** Displacement of platform drivers arrives as hours cut, not as unfilled vacancies: the flows view now carries a "hours cut" destination, and by 2040 about 19 k U.S. FTE and 740 k in China have gone through it. Because the embodied channel is small before 2035 and the software channel still runs through attrition, jobs below baseline still fall on workers under 25 (52%) and 25–44 (41%). The embodied layer will change that in scenarios with fast ramps, where layoffs and hours cuts hit incumbents; the layoff share for site conversions (P.122) is the lever.

## 3. What the regions say

| 2040 Q4, median | Employment | Embodied share of task-hours | Robotaxi-class fleet | Manipulator fleet |
|---|---|---|---|---|
| US | −4.8% | 5.4% | 0.40 M | 4.5 M |
| EU | −4.9% | 6.0% | 0.41 M | 6.5 M |
| CN | −1.7% | 6.5% | 1.59 M | 24.8 M |
| IN | −3.3% | 5.1% | 0.15 M | 21.7 M |
| JP | −2.1% | 5.8% | 0.12 M | 1.9 M |

China leads on fleets because its approval path is the fastest and its employment base the largest; India's fleet is large because manipulators are profitable at any wage once the unit cost falls, which is the point in finding 2. Both regions' occupation structures are still fixtures, so the composition of what is displaced there is imputed.

## 4. What surprised me

- **The classifier alone reorganises the physical economy.** One channel per task group puts 20% of U.S. task-hours on the manipulation clock, 1.9% on driving, 1.6% on fixed automation, and 1.6% out of reach (care, surgery, dexterity). v0.2's single robotics clock had treated all of it as one slow block; the split matters more than any parameter in the block.
- **Adjacent jobs are real but small.** Fleet operations, remote assistance and hardware production add 0.35 M U.S. jobs by 2040 against 2.1 pp of embodied displacement, a ratio the adjacent-jobs coefficients (P.120, E) set directly. The channel bar is +0.25 pp.
- **The baseline automation-trend lever does almost nothing** because the fixed-automation increment is 1.6% of task-hours. The trend matters through the manipulation classifier boundary (structured versus unstructured), not through the fixed class.

## 5. What I do not trust yet

- The three manipulation unit-economics numbers above, the driving clock's start and doubling time, the approval baseline paths, and the 2025 cumulative production figures: all V?, all E, all pending the data plan of §A.10.
- The self-employed stock is a fixture from major-group shares; India and the rest of Asia get very large stocks (135 M and 104 M FTE) that partly re-label the informal sector the model says it excludes. Read the non-U.S. self-employed numbers as placeholders.
- The channel classifier misassigns some tasks (a delivery driver's loading task is manipulation; a nurse's "transport patients" task is `none`). It cannot double count, but it can misplace; the column is exposed in the Occupations view so a reader can check.
- Runtime is 67 s for the full pipeline against a 60 s budget; the embodied layer costs about half a second per central run, the extra tornado parameters and channel runs cost the rest.

## 6. Reproducibility

`make data` rebuilds the four application tables and the channel column; `uv run aiwsim run --scenario scenarios/baseline.json` reproduces the document (hash `sha256:7d06b57f81bc7fc0b7b8b8e5` on this commit); `sim/tests/test_applications.py` runs the exclusivity, deployment-bound, frozen-embodiment, regional-ordering, monotonicity, approval-path and self-employed-margin checks. Sixty simulation tests, five API tests, and the web suite pass.
