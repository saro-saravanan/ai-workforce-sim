# Findings so far — Phase 4 (chat, insights, briefs)

Phase 4 adds the Claude-backed analyst interface, deterministic insight ranking, and shareable briefs. Nothing in the simulation core changed; every number below comes from the same cached results documents the UI reads.

## What was built

- **Chat layer** (`api/aiwsim_api/chat.py`, `POST /api/chat`): a manual tool loop over `client.beta.messages.create` (Claude Opus 5, adaptive thinking, server-side refusal fallback). Thirteen strict-schema tools read results documents and run scenarios; the model has no other way to obtain a number. The reply carries the tool log so the UI shows what grounded it.
- **Propose → confirm → run, enforced in code.** `propose_scenario` validates a child scenario against the schema and returns the annotated diff without running it. `run_scenario` on a proposal the client has not listed in `confirmed_proposals` returns `needs_confirmation` to the model; the test suite checks this refusal happens server-side, not by prompt alone.
- **Insights** (`api/aiwsim_api/insights.py`, `GET /api/insights/{hash}`): twelve candidate findings computed from the results document, each with statement, mechanism (spec section and parameter), confidence inherited from the run's classification, and a surprise score used for ranking. With `compare=` a further set describes what the scenario changed against a reference run, paired over common draws. No model call is needed, so the UI's insight cards work without credentials.
- **Briefs** (`api/aiwsim_api/brief.py`, `GET /api/brief/{hash}?format=md|html`): headline table with bands and sign confidence, lever diff, optional paired comparison, the top three findings, model notes, sensitivity table, regional table, method and provenance, scenario JSON appendix. Byte-for-byte deterministic; the optional model-written narrative is appended under a heading that says so.
- **Web**: an `Ask` tab beside `Explain`, proposal cards with Run and Edit, insight cards, and an `Export brief` menu; mock mode answers with canned replies and the mock document's insights.
- **Terminal**: `python -m aiwsim_api.chat "question" --hash sha256:… [--confirm prop-…]`.

## What the insight ranker says

Run on the consensus baseline (200 draws), the two presets, and the example what-if (100 draws each), the top three deterministic findings are the same in every case:

| Rank | Finding | Baseline statement |
|---|---|---|
| 1 | The demand multiplier dominates | P.87 moves 2040Q4 employment from −4.2% to +11.5% across its literature range, a swing 3.0× the next parameter, and is the one parameter that flips the sign |
| 2 | Displacement runs through hiring, not layoffs | Of 5.5M jobs below baseline by 2040Q4, 100% are positions not refilled after attrition |
| 3 | Young entrants carry the adjustment | Workers aged 16–24 absorb 49% of jobs below baseline against a 13% employment share |

That invariance is itself the finding: the surprising properties of this model are structural, not scenario-specific. Two of the three follow from one design choice (the hiring channel absorbs contraction before layoffs, spec §5.3) and the third from the demand feedback (spec §6.2). A reader who accepts those two mechanisms should not be surprised by anything else the model says; a reader who rejects them should discount the employment path entirely. This is why the brief prints mechanism next to every finding.

When a reference run is supplied, the ranker adds paired-delta findings and these do change by scenario:

- **Acemoglu 2024 preset vs baseline**: GDP −3.1 pp at 2040Q4 (10–90: −8.6 to −0.6, band excludes zero) and wage share +1.4 pp, from four levers (intensity ceiling 0.7→0.4, price pass-through 0.7→0.5, reinstatement, demand elasticity). This ranks first.
- **Goldman 2023 preset vs baseline**: employment +1.3 pp and GDP +0.9 pp, both bands including zero at 100 paired draws. The presets differ mainly in the central path, not in what the Monte Carlo can distinguish.
- **EU AI Act delayed two years + DeepSeek open frontier 2027 vs baseline**: every U.S. headline delta is within ±0.3 pp, and the EU itself moves by 0.01 pp on employment. The ranker reports this as "barely moves headline outcomes" and points at the regional series. It is consistent with Phase 3's finding that the AI Act lever is weak in the model (compliance friction acts on a small high-risk task share), and it is the kind of null result the chat layer should say out loud rather than dress up.

## What surprised me

1. **A scenario-invariant top three.** I expected the ranker to surface different findings per preset. It did not, and adding the paired-delta candidates was the right fix rather than tuning the scores: "what is surprising about this model" and "what did this scenario change" are different questions and the UI now asks both.
2. **The Goldman preset's tornado.** Under that preset the demand multiplier's high end takes 2040Q4 employment to +26%, and eight parameters can flip the employment sign (one in the baseline). Optimistic presets are not more certain, they are more sensitive.
3. **How little prompt the guardrails need.** Once numbers can only come from tools, and the run tool refuses unconfirmed proposals, the system prompt reduces to seven short rules. The scripted-client tests exercise the loop end to end (propose, refused run, confirmed run, paired compare, tool error as `is_error`) in under twenty seconds without credentials.

## What I do not trust yet

- **No live model call has been made from this environment.** The sandbox has no API key, so the loop has been exercised only with a scripted fake client. The request shape follows the current SDK (beta create, `betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`, strict tools); a first real session should check tool-selection quality and the length of replies, and adjust the rules in `SYSTEM`.
- **Surprise scores are hand-set.** The weights in `candidate_insights` encode my priors (for example that a 13% employment share absorbing 49% of losses is surprising). They are transparent and cheap to change, but they are not calibrated against readers.
- **Paired comparison is U.S.-only.** `compare_runs` and the delta insights read the U.S. per-draw arrays; regional deltas come from the central series only. The EU null result above therefore rests on central values.
- **Brief narrative is optional and labelled.** The deterministic brief is the deliverable; the model-written narrative is appended only when the user includes a reply, and the heading says it is model-written.

## Runtime and reproducibility

| Item | Value |
|---|---|
| API tests (5, incl. three chat flows with 8-draw runs) | ~18 s |
| Simulation core tests | 49 passed, ~62 s |
| 100-draw preset run, ten regions, full ensemble and tornado | ~24 s |
| Insight ranking / brief generation | < 50 ms, deterministic |

Chat requires `ANTHROPIC_API_KEY` on the API server; `GET /api/chat/status` reports availability and the UI degrades to insight cards and briefs when it is absent.

## Screenshots (mock mode)

`docs/screenshots/phase4-ask-insights-{light,dark}.png` (Ask tab with insight cards), `phase4-proposal-{light,dark}.png` (proposal card with diff, Run and Edit), `phase4-export-menu-{light,dark}.png` (brief export).
