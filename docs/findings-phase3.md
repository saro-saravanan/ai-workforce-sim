# Findings so far — Phase 3 (EU and Asia, AI supply side, rents)

Date: 2026-09-02. Spec v0.2 with §16 implementation notes. Scenario `baseline`, 200 draws, 8-cell structural ensemble, ten regions run jointly through a shared capability clock. Everything is relative to each region's frozen-AI baseline. Bands are 10th to 90th percentile. **Every non-U.S. occupation structure is a fixture** (U.S. task mix tilted by income); the numbers below are composition effects plus the regional access lag, wage level, regulation, and rent flows, and should be read as the model's mechanism speaking, not as regional data.

## What the model currently says, 2040 Q4

| Region | Employment | GDP | Real wages | AI rents received ($bn/yr) | Net AI trade ($bn/yr) |
|---|---|---|---|---|---|
| US | −3.0% [−6.3, +1.2] | +6.9% [+4.1, +12.3] | +4.5% | 120 | +258 |
| EU | −2.1% [−6.4, +1.9] | +4.9% [+1.6, +9.5] | +4.2% | 28 | −2 |
| UK | −2.6% [−7.0, +1.4] | +4.9% [+1.6, +9.6] | +4.4% | 5 | −7 |
| CN | +1.4% [−2.6, +5.1] | +4.4% [+1.9, +8.2] | +2.9% | 38 | −1 |
| JP | +0.2% [−5.6, +5.0] | +4.8% [+1.0, +9.6] | +2.6% | 8 | −13 |
| KR | +0.6% [−4.2, +6.3] | +8.8% [+5.4, +15.5] | +3.7% | 3 | +48 |
| IN | −0.8% [−2.8, +1.6] | +3.2% [+1.2, +6.0] | +2.7% | 4 | −8 |
| TW | +2.0% [−2.0, +9.4] | +13.7% [+10.4, +22.5] | +3.4% | 22 | +89 |
| SG | −2.7% [−6.4, +1.7] | +6.5% [+3.5, +11.9] | +4.5% | 2 | 0 |
| RoA | −0.9% [−3.0, +1.7] | +3.1% [+1.0, +6.0] | +2.8% | 3 | −9 |

Rents by 2040 accrue 52% to the U.S., 16% to China, 12% to the EU. The U.S. employment effect is unchanged from Phase 2 at −3.0%; U.S. GDP rose from +6.0% to +6.9% because the U.S. now receives net AI trade income of about $258bn a year (model-stage rents from every region, the design share of hardware, and compute hosted in U.S. data centers).

## Three findings from Phase 3

1. **The countries hit hardest by displacement are the ones that collect the rents.** The U.S., Singapore, and the UK have the largest employment effects and the highest rent receipts per worker; China and Japan show small positive employment effects. The mechanism is not exposure, which is similar everywhere in the fixture. It is that high-wage regions with full frontier access adopt first and deepest, while China's four-quarter access lag and low wages (which fail the task-level profitability test for more occupations) slow substitution, and Japan's shrinking baseline workforce means attrition absorbs the gap with room to spare. The static reports rank countries by exposure; the model ranks them by adoption and access, and the order changes.
2. **The AI hardware trade is a bigger regional story than model rents.** Taiwan's GDP is +14% and Korea's +9% by 2040 because the hardware half of the $700bn-a-year capex path is booked as their exports (fabrication 20%, memory 15%, U.S. design 55%, EU equipment 10%). Model-stage rents are $37bn to U.S. labs and $21bn to Chinese labs; the hardware flow to Taiwan alone is four times the Chinese labs' rents. If the tool is cited for "who wins from AI", this is the line to cite, and it rests on one estimated value-added split (risk #25).
3. **The EU AI Act barely matters for EU displacement; access lag and wages matter more.** The EU's employment effect is smaller than the U.S. one mostly because the fixture gives it a lower wage level and a one-quarter access lag, not because of the Act. The Act enters only through the high-risk use-case share (about 5% of task-hours) and a one-quarter delay. The "EU delay" scenario therefore moves EU employment by a fraction of a point. A chief economist should expect the Act to show up in the compliance-cost premium and availability lag, both of which are estimates with wide ranges.

## What surprised me

- **Vectorizing across regions was the only way to make ten regions affordable.** Looping over regions cost 57 seconds at 200 draws because of Python overhead, independent of draw count; stacking regions onto a second batch axis brought it to 18 seconds, and storing occupation-level histories only for the central draw outside the U.S. was what made the memory fit.
- **One fixture inconsistency produced negative employment.** Rest-of-Asia's fixture wage bill exceeded its GDP, which made the demand feedback loop unstable and drove one occupation's employment below zero. The loader now scales fixture wages to at most 55% of GDP and the demand multiplier is clamped; both are recorded in spec §16 and the region's provenance.
- **The example scenario finally does something.** With regions in place, "EU delays the AI Act two years and DeepSeek releases an open frontier model in 2027" changes EU access and shifts model-stage rents toward China; in Phase 2 it had nothing to act on.

## What I do not trust yet

1. **Regional occupation structure** (risk #23). Everything outside the U.S. is the U.S. task mix tilted by income. ILOSTAT and Eurostat ingest scripts are written and untested against the live sites.
2. **Access lags, actor lags, and prices** (risk #24) are transcribed judgement; the Epoch ingest replaces release history. Market shares are static over time.
3. **Hardware value-added split** (risk #25). Taiwan's and Korea's GDP numbers are this one table.
4. **Cohorts outside the U.S.** use U.S. age, education, and decile shares.
5. **Trade linkage is inert** until the sector fixture is replaced: everything is non-tradable, so the foreign-demand channel does nothing yet.
6. **Regional GDP baselines** are Natural Earth 2019 estimates grown at assumed long-run rates.

## Runtime and reproducibility

Ten regions, 200 draws, ensemble: 17.6 s; tornado 6.5 s; channels 2.0 s; total 30.5 s on 4 cores. Document 9.8 MB, gzip-served. Same hash and seed give identical percentiles. `make setup && make data && make run` reproduces this note.
