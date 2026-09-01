# Wireframes v0.1 (low fidelity)

Single-page app. One scenario, one time scrubber, seven views. Every view reads the same cached run. Dark/light themes; projector-legible (min 14 px labels, 4.5:1 contrast, bands as translucent fills, never more than two hues per chart plus a neutral).

## App shell

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ◉ AI Workforce Sim   Scenario: [Consensus central ▾] [+ New] [Compare] [Share ⧉]     │
│ Views: [Map] [Flows] [Occupations] [Cohorts] [Economy] [AI Supply] [Compare]  ⋯ [☾]  │
├──────────────────────────────────────────────────────────────┬───────────────────────┤
│                                                              │ Chat / Explain        │
│                                                              │ ┌───────────────────┐ │
│                        ACTIVE VIEW                           │ │ "What if the EU   │ │
│                                                              │ │ delays the AI Act │ │
│                                                              │ │ by two years…"    │ │
│                                                              │ └───────────────────┘ │
│                                                              │ ▸ Proposed diff (3)   │
│                                                              │   regulation.EU…      │
│                                                              │   shocks[+1]          │
│                                                              │   [Run] [Edit]        │
│                                                              │ ▸ Insights (3) after  │
│                                                              │   run, each w/ conf.  │
├──────────────────────────────────────────────────────────────┴───────────────────────┤
│ 2024 ─────●──────────────────────────────────────────────────────────────── 2040     │
│ ◀ ▶ ▐▐  2029 Q3   Region: [US ▾] › [All states ▾]   Metric: [Net employment ▾]       │
│ Band: [10–90 ▾]  Baseline: no AI progress after 2023  Confidence legend ● high ◐ ○   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

The scrubber is global. Dragging it re-renders every view from cached arrays (no re-run). The chat panel collapses to an icon on narrow screens.

## 1. World map

```
┌──────────────────────────────────────────────────────────────┐
│ Net employment effect vs baseline, 2029 Q3       [◐ medium]  │
│                                                              │
│      ▒▒▒▒▒▒                ░░░░░                             │
│    ▒▒▒▒▒▒▒▒▒▒     ░░░░░░░░░░░░░░░░                          │
│   ▒▒▒ US ▒▒▒▒    ░░ EU ░░░   ▓▓▓ CN ▓▓  ░ JP                │
│    ▒▒▒▒▒▒▒▒       ░░░░░░░    ▓▓▓▓▓▓▓    KR                   │
│      ▒▒▒▒           ░░░        ▓▓ IN ▓  TW SG                │
│                                                              │
│  −6%  ▓▓▓▓ ▒▒▒▒ ░░░░ ████  +2%        (diverging, neutral 0) │
│  ▸ Click a region to drill: US → states, EU → members        │
│  Hover: US  −2.1% [−3.4, −0.9]  employment; wages +0.4%      │
└──────────────────────────────────────────────────────────────┘
```

Drill-down replaces the world with the country; breadcrumb `World › US › Ohio`. Hatched fill for regions where data is imputed (China, Rest of Asia). Metric switch: employment, wages, wage share, AI rents captured.

## 2. Labor flow Sankey

```
┌──────────────────────────────────────────────────────────────┐
│ Where displaced workers went, 2024 → 2029 Q3 (cumulative)    │
│                                                              │
│ Displaced ═══════════╗                                       │
│  from:               ╠═════════▶ Same occupation, new firm   │
│  Office/admin ███    ╠═══════▶ New occupation, same sector   │
│  Customer svc ██     ╠═════▶ New sector                      │
│  Software     ██     ╠═══▶ Retraining ──▶ (re-employed 55%)  │
│  Legal supp.  █      ╠══▶ Long-term unemployed               │
│  Finance ops  █      ╠═▶ Exited labor force                  │
│  Other        ██     ╚▶ Retired                              │
│                                                              │
│ Toggle: [cumulative | this quarter]  Cohort filter: [All ▾]  │
│ Flow widths carry the median; hover shows the band.          │
└──────────────────────────────────────────────────────────────┘
```

Left nodes = origin occupation clusters (top 6 + other). Right nodes = labor-market states. Time scrubber changes the cumulative window.

## 3. Occupation heatmap

```
┌──────────────────────────────────────────────────────────────┐
│ Exposure vs realized displacement, 2029 Q3                   │
│  Realized displacement (share of 2023 jobs)                  │
│  30% ┤                                   ○ Customer service  │
│      │                            ● Paralegals              │
│  20% ┤                       ○ Bookkeepers                   │
│      │                   ● Translators                       │
│  10% ┤            ○ Software devs  ◯ Accountants             │
│      │      ○ Nurses         ○ Financial analysts  ◯ Lawyers │
│   0% ┼──○───○─────◯──────────────────────────────────────── │
│      0%   20%   40%   60%   80%   Exposure (S+G at C→∞)      │
│  Size = employment. Fill = confidence. Diagonal = "as exposed│
│  as hit". Below-diagonal, large circles = exposed, not yet   │
│  hit: the tool's headline visual.                            │
│  [Table view] [Sort by gap ▾]                                │
└──────────────────────────────────────────────────────────────┘
```

Alternative rendering (toggle): a true heatmap, rows = occupation clusters sorted by exposure, columns = quarters, color = realized displacement. The scatter is the default because the gap is the insight.

## 4. Cohort view

```
┌──────────────────────────────────────────────────────────────┐
│ Outcomes by cohort, US, 2029 Q3       Metric: [Employment ▾] │
│                                                              │
│  Age            Education           Income decile            │
│  16–24 ▓▓▓▓▓▓▓  <HS     ▓▓▓         1 ▓▓                     │
│  25–44 ▓▓▓▓     HS      ▓▓▓▓▓       2 ▓▓▓                    │
│  45–54 ▓▓       Some c. ▓▓▓▓▓▓      … ▓▓▓▓▓▓                 │
│  55+   ▓▓▓      BA+     ▓▓▓▓▓▓▓▓    9 ▓▓▓▓▓▓▓▓               │
│        −8%  0            −8%  0      10 ▓▓▓▓                 │
│                                                              │
│  Small multiples: each bar carries its 10–90 band as a thin  │
│  whisker. Click a bar to cross-filter the other two panels   │
│  (e.g., 16–24 × BA+).                                        │
│  Note: "BA+ hit harder than HS" is the kind of finding the   │
│  static reports miss; the panel is built to make it visible. │
└──────────────────────────────────────────────────────────────┘
```

## 5. Economy dashboard

```
┌──────────────────────────────────────────────────────────────┐
│ US economy vs no-AI baseline                 [Region: US ▾]  │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│ │ GDP  +3.1%   │ │ Productivity │ │ Wage share   │           │
│ │ [1.2, 5.4]   │ │ +2.4%/yr…    │ │ −1.8 pp      │           │
│ │ ╱╱╱▒▒▒▒▒▒    │ │ ╱╱▒▒▒▒▒▒     │ │ ╲╲▒▒▒▒▒▒     │           │
│ └──────────────┘ └──────────────┘ └──────────────┘           │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│ │ Gini +0.012  │ │ Tax base     │ │ AI rents to  │           │
│ │              │ │ −0.6%        │ │ region 85%   │           │
│ │ ╱▒▒▒▒▒▒▒     │ │ ╲▒▒▒▒▒▒      │ │ ▬▬▬▬▬▬▬      │           │
│ └──────────────┘ └──────────────┘ └──────────────┘           │
│ Each tile: headline at scrubber time, band, sparkline with   │
│ 10–90 fill and median line, dotted baseline. Click expands   │
│ to full chart with channel decomposition stacked below:      │
│   displacement ▓  augmentation ░  new tasks ▒  demand ▪ capex│
└──────────────────────────────────────────────────────────────┘
```

## 6. AI supply timeline

```
┌──────────────────────────────────────────────────────────────┐
│ Capability, cost, and rules on one axis                      │
│ Capability (task horizon)                                    │
│ 1 wk ┤                                    ╱╱▒▒▒▒▒▒▒▒▒▒▒     │
│ 1 d  ┤                          ╱╱▒▒▒▒▒▒▒                    │
│ 1 h  ┤              ╱╱▒▒▒▒                                   │
│ 10 m ┤   ╱╱▒▒▒                                               │
│      ┼────┬────┬────┬────┬────┬────┬────┬────┬────           │
│ Price│ ╲                                                     │
│ $/Mtok╲╲╲╲╲____                                              │
│      ┼────┬────┬────┬────┬────┬────┬────┬────┬────           │
│ Releases  ● OpenAI  ● Anthropic  ● Google  ● DeepSeek(open)  │
│           ●   ●  ●   ●  ● ●   ○   ●   ●                     │
│ Rules     ▮ EU AI Act GPAI  ▮ high-risk  ▮ export ctrl  ▮ CO │
│      2024   2025   2026   2027   2028   2029   2030 …        │
│ Region filter shades what is NOT available in the region.    │
│ Scenario shocks appear as flagged markers (⚑ open-weights).  │
└──────────────────────────────────────────────────────────────┘
```

## 7. Scenario compare

```
┌──────────────────────────────────────────────────────────────┐
│ A: Consensus central   vs   B: EU delay + DeepSeek 2027      │
│ What changed (3):  regulation.EU.ai_act baseline→delayed_2y  │
│                    shocks[+] open_weights_release deepseek…  │
│                    P.61 unchanged (inherited)                │
│ ┌────────────────────────────┬────────────────────────────┐  │
│ │ A  EU employment           │ B  EU employment           │  │
│ │    ▒▒▒▒▒▒▒▒▒▒▒▒            │    ▒▒▒▒▒▒▒▒▒▒▒▒▒▒          │  │
│ └────────────────────────────┴────────────────────────────┘  │
│ Δ (B − A)   ▁▁▂▂▃▃▄▄▅▅▅▅   EU emp −0.9 pp [−1.6, −0.3] ● high│
│             EU GDP +0.7 pp [0.2, 1.3] ◐ medium               │
│             US AI rents −4 pp [−7, −1] ● high                │
│ Why: (mechanism trace) earlier EU availability → adoption    │
│  +6 pp by 2029 → displacement in admin/finance ops; open     │
│  weights cut price 4× in EU and CN → US actor revenue share ↓ │
│ [Swap] [Open in map] [Export brief]                          │
└──────────────────────────────────────────────────────────────┘
```

Any view can be put in compare mode; the delta strip and the "why" trace are always present.

## Interaction rules
- Scrubber, region, metric, and band selection are URL state; a link reproduces the exact view.
- Confidence glyphs (●◐○) appear next to every headline number.
- Imputed data is hatched; estimated parameters (`E`) are marked in tooltips.
- No animation longer than 300 ms; scrubber playback at 4 quarters/second.
- Keyboard: ← → move one quarter; space play/pause; 1–7 switch view.
