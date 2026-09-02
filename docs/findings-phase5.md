# Findings so far — Phase 5 (polish, public demo, methodology)

*Phase 5 added no new mechanism. It made the shipped model consistent with itself, wrote the methodology down, and produced a serverless public demo. Numbers below are the 200-draw, ten-region baseline after the fix in §1.*

## 1. A consistency bug the phase found and fixed

The Monte Carlo's central line and a single central run disagreed. The Bass imitation coefficient `q` (P.42) is fitted to the BTOS adoption series; single runs used the fitted value while the Monte Carlo's draw 0 used the registry central (0.38), so the dashed central line in every chart since Phase 2 showed adoption of 65% in 2030 Q4 where a single run showed 77%. Draws now re-centre on the fitted value (an explicit override of P.42 still wins), a test asserts that draw 0 equals the single run, and spec §16 records the change.

The correction moves the central line, not the bands, and only where adoption speed matters:

| U.S., central draw | Before | After |
|---|---|---|
| Adoption 2030 Q4 (employment-weighted) | 65% | 77% |
| Employment 2030 Q4 | −1.3% | −1.8% |
| Employment 2040 Q4 | −3.0% | −3.1% |
| GDP 2040 Q4 | +6.9% | +7.3% |
| Real wages 2040 Q4 | +4.5% | +4.8% |

The medians and bands (which the findings notes of Phases 2–4 quote) are unchanged: employment −2.5% [−6.5, +1.2], GDP +6.8% [+4.1, +12.6], real wages +3.1% [+1.9, +6.5], wage share −3.5 pp [−4.8, −2.1] in 2040 Q4, sign confidence low for employment and high for the rest.

## 2. What the model says at the end of the build

- **Output up, employment slightly down, real wages up, wage share down.** The same four statements as Phase 2, now with an identical central line in the CLI, the API, and the UI.
- **The employment sign is the open question.** The demand multiplier is the one parameter that flips it in the baseline; the structural spread across the eight mechanism cells (6.1 pp) exceeds the parametric spread within a cell (5.7 pp). The tool reports this as low confidence and says why.
- **The hiring channel decides who pays.** At the central attrition rate every shipped scenario, including a 3-month doubling time, closes the gap through unfilled vacancies: layoffs are zero, and workers aged 16–24 carry about half of jobs below baseline against a 13% employment share.
- **Realized displacement peaks near 7% of task-hours within a decade** in every shipped scenario, so the new validity flag for the reduced-form labor rules (15% within ten years, spec §12) never triggers. The intensity ceiling and the profitability test, not the capability clock, cap it; a faster clock brings the same displacement forward rather than adding to it.
- **Regions differ by composition, not mechanism.** The EU and U.S. differ by 0.3 pp of employment in 2040; China's four-quarter access lag and low-wage tier place its employment effect above zero; rents concentrate in the U.S. and the chip producers. Non-U.S. occupation structures remain fixtures.

## 3. Presets after the fix

The Acemoglu and Goldman replication tests still pass at their tolerances. Their bands are wider than their central lines suggest: when a preset sets a lever at the edge of the literature range (the Acemoglu intensity ceiling of 0.4 is the registry minimum), the triangular draw distribution is one-sided, so the median draw sits well above the central line (2040 adoption 92% median against 74% central). This is the documented "range widens to include the lever" rule doing its job, and a reader comparing presets should compare central lines.

## 4. The public demo

`python -m aiwsim_api.export_static` runs the shipped scenarios (baseline, the EU delay example, three presets) and writes every document the web app reads into `web/public/static/` (about 13 MB for two scenarios at 12 draws before compression; runs dominate). The web app in static mode reads those files, disables what needs a live engine (new scenarios, chat), and keeps compare, explain, insights, and briefs, which are client-side or precomputed. The Pages workflow (`.github/workflows/pages.yml`) rebuilds the export on every push to the default branch; enabling Pages with source "GitHub Actions" in the repository settings is the one manual step. The full document set ships uncompressed; GitHub Pages serves it gzip-encoded (about 1.5 MB per run).

## 5. What I do not trust yet

Unchanged from Phase 4, and written down in `docs/methodology.md` §7 and `docs/risks.md`: the feasibility thresholds, the regional fixtures, and the untested live behaviour of the chat prompt. Phase 5 adds one more: the export is a snapshot, and a demo that outlives its workflow run will show stale numbers without saying so beyond `meta.run_at`.

## 6. Runtime

Ten regions, 200 draws, tornado, channels: 20–28 s per scenario on the 4-core sandbox. The static export of five scenarios takes about two and a half minutes plus the data build. Test suites: 51 (simulation core), 5 (API, including the chat fake), 72 and rising (web).
