# 2026 hold-out (review §2.2, item 2)

Refit to 2025 only: market-price multiple P.143 = 8.0 (shipped 5.0), layoff-first share = 0.15 (shipped 0.25). Central U.S.-only runs; the shipped fit used the 2026 rows too.

| Series | Quarter | Observed | Shipped model | Shipped error | Refit-to-2025 model | Refit error |
|---|---|---|---|---|---|---|
| Announced AI-cited job cuts since 2023 (Challenger) | 2026Q2 | 173,568.0 | 152,126.4 | -12% | 96,806.1 | -44% |
| AI industry revenue (world, $bn/yr) | 2026Q4 | 140.0 | 48.6 | -65% | 56.7 | -60% |
| Firms using AI (BTOS, %) | 2026Q1 | 18.0 | 13.0 | -28% | 12.4 | -31% |
| Firms using AI (BTOS, %) | 2025Q4 | 17.3 | 12.0 | -31% | 11.5 | -34% |

Grid searched (absolute log error against the 2025 row): P.143 3.0: 0.813, 4.0: 0.744, 5.0: 0.684, 6.0: 0.629, 7.0: 0.581, 8.0: 0.539; layoff share 0.1: 0.183, 0.15: 0.131, 0.2: 0.369, 0.25: 0.56, 0.3: 0.72, 0.4: 0.978, 0.5: 1.181.

