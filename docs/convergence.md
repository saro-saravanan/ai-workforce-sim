# Monte Carlo convergence (review §2.5)

Baseline, U.S.-only, no tornado or channels. 2040Q4 employment versus the frozen-AI path, percent; GDP p50 for reference.

| Draws | Seed | p10 | p50 | p90 | GDP p50 | Confidence label |
|---|---|---|---|---|---|---|
| 64 | 42 | -12.41 | -8.55 | -4.84 | 5.49 | high |
| 64 | 7 | -11.89 | -8.72 | -5.00 | 5.76 | high |
| 64 | 99 | -12.74 | -8.66 | -4.46 | 5.99 | high |
| 128 | 42 | -12.40 | -8.64 | -4.66 | 5.53 | high |
| 128 | 7 | -12.35 | -8.73 | -4.23 | 5.81 | high |
| 128 | 99 | -12.49 | -8.56 | -4.75 | 5.99 | high |
| 256 | 42 | -12.06 | -8.66 | -4.75 | 5.73 | high |
| 256 | 7 | -12.49 | -8.46 | -4.20 | 5.84 | high |
| 256 | 99 | -11.88 | -8.52 | -4.77 | 5.97 | high |
| 384 | 42 | -12.12 | -8.63 | -4.67 | 5.75 | high |
| 384 | 7 | -12.35 | -8.53 | -4.40 | 5.81 | high |
| 384 | 99 | -12.24 | -8.47 | -4.91 | 5.93 | high |

Across-seed standard deviation (points):

| Draws | p10 | p50 | p90 | Labels seen |
|---|---|---|---|---|
| 64 | 0.43 | 0.09 | 0.28 | high |
| 128 | 0.07 | 0.09 | 0.27 | high |
| 256 | 0.31 | 0.10 | 0.32 | high |
| 384 | 0.11 | 0.08 | 0.25 | high |

Reading: the band edges move with the seed at low draw counts; the draw count in the baseline scenario should be the smallest at which the p90 edge is stable to about half a point and the confidence label does not change with the seed.
