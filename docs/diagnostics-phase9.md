# Threshold-seed sensitivity (review §2.4)

`aiwsim diag threshold-seeds --seeds 0,1,2 --regions US` on the baseline scenario, central run (draw 0), no tornado or channels (rerun after Phase 9b's data refresh and the BEA table; the Phase 9 values were −2.54 / −7.31). Seed 0 is the reference hash of the task key; seeds 1 and 2 append the seed to the key before hashing, which re-spreads every task group's threshold within its occupation's range. Occupation effects are 2040Q4 employment versus the frozen-AI path; the rank correlation and the top-decile overlap compare each seed's ranking of the 831 occupations with seed 0.

| Seed | Employment 2030 (%) | Employment 2040 (%) | Δ vs seed 0 (pp) | GDP 2040 (%) | Spearman ρ, occupation effects 2040 | Top-decile overlap | Max occupation change (pp) |
|---|---|---|---|---|---|---|---|
| 0 | -2.86 | -7.12 | +0.00 | +6.94 | 1.0000 | 1.00 | 0.00 |
| 1 | -2.86 | -7.12 | +0.00 | +6.94 | 0.9999 | 1.00 | 0.88 |
| 2 | -2.86 | -7.12 | +0.00 | +6.94 | 0.9999 | 1.00 | 3.94 |

Reading: the headline and the ordering of occupations do not depend on the seed; an individual occupation's number can move by up to four points when it has few task groups. The engine's resolution is therefore a few points per occupation and a decile in rank. The classifier audit sample for the companion check is `docs/classifier-audit-sample.md`; the exposure-source swap (GPTs-are-GPTs against an alternative exposure rating) is not done.
