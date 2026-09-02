/**
 * Client-side port of a subset of api/aiwsim_api/insights.py and brief.py, used only in mock mode
 * (`VITE_USE_MOCK=1`) where no API server answers /api/insights and /api/brief. The real app reads
 * both from the API; nothing here is used when a server is present.
 */
import type { ResultsDocument, Series, TornadoRow } from '@/types/results'
import type { Insight, InsightsResponse } from '@/types/chat'
import { seriesFor } from '@/lib/world'
import { renderMarkdown, escapeHtml } from '@/lib/markdown'
import { FLOW_DESTINATIONS } from '@/types/results'

type Pct = 'p10' | 'p50' | 'p90' | 'central'

function at(s: Series | undefined | null, t: number, key: Pct = 'p50'): number {
  const arr = s?.[key] ?? s?.central ?? s?.p50
  return arr?.[t] ?? 0
}
function sgn(v: number, nd = 1, unit = '%'): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(nd)}${unit}`
}
function band(s: Series | undefined | null, t: number, unit = '%', nd = 1): string {
  const p50 = at(s, t)
  if (s?.p10 && s.p90)
    return `${sgn(p50, nd, unit)} (10–90: ${sgn(at(s, t, 'p10'), nd, unit)} to ${sgn(at(s, t, 'p90'), nd, unit)})`
  return sgn(p50, nd, unit)
}
const clip = (x: number) => Math.max(0, Math.min(1, x))
function confOf(doc: ResultsDocument, metric: string, q: string): string {
  return (
    (doc.confidence as Record<string, Record<string, { level: string }> | undefined>)?.[metric]?.[q]
      ?.level ?? 'n/a'
  )
}
export function tornadoSwing(r: TornadoRow): number {
  return Math.abs(r.effect_at_high - r.effect_at_low)
}
export function tornadoFlips(r: TornadoRow): boolean {
  return (
    Math.sign(r.effect_at_low) !== Math.sign(r.effect_at_high) &&
    r.effect_at_low !== 0 &&
    r.effect_at_high !== 0
  )
}

/**
 * Deterministic candidate insights, sorted by surprise. Ported candidates: output up while
 * employment down, the hiring channel (from `flows.destinations`), the dominant sensitivity
 * parameter, regional divergence, and sign confidence.
 */
export function candidateInsights(doc: ResultsDocument, region = 'US'): Insight[] {
  const quarters = doc.meta.quarters
  const tEnd = quarters.length - 1
  const qEnd = quarters[tEnd] ?? ''
  const blk = seriesFor(doc, region) ?? doc.series.US
  const out: Insight[] = []
  const add = (
    key: string,
    title: string,
    statement: string,
    mechanism: string,
    confidence: string,
    surprise: number,
    evidence: Record<string, unknown>,
    metric: string | null = 'employment_pct_vs_baseline',
    quarter = qEnd,
  ) =>
    out.push({
      key,
      title,
      statement,
      mechanism,
      confidence,
      surprise: Number(clip(surprise).toFixed(3)),
      evidence,
      metric,
      quarter,
      region,
    })

  const e = blk?.employment_pct_vs_baseline
  const g = blk?.gdp_pct_vs_baseline
  const rw = blk?.real_wage_pct_vs_baseline
  if (e && g) {
    const e50 = at(e, tEnd)
    const g50 = at(g, tEnd)
    if (g50 > 0 && e50 < 0)
      add(
        'gdp_vs_employment',
        'Output rises while employment falls',
        `In ${region}, GDP is ${band(g, tEnd)} above the no-AI baseline by ${qEnd} while employment is ${band(e, tEnd)}; real wages are ${rw ? band(rw, tEnd) : 'n/a'}.`,
        'Task automation lowers unit costs (spec §5.2); demand responds with elasticity η_s and the demand multiplier m (P.87), but below unit elasticity the output gain does not refill the displaced task-hours (spec §5.2–5.3).',
        confOf(doc, 'employment_pct_vs_baseline', qEnd),
        0.35 + Math.min(0.4, Math.abs(e50) / 10) + Math.min(0.25, g50 / 20),
        {
          gdp_pct_vs_baseline: g50,
          employment_pct_vs_baseline: e50,
          real_wage_pct_vs_baseline: rw ? at(rw, tEnd) : null,
        },
      )
  }

  // hiring channel: the mock document carries the flows section rather than laid_off/unhired series
  const dest = doc.flows?.destinations
  if (dest && region === 'US') {
    const unfilled = at(dest.unfilled_entry, tEnd)
    const tot = FLOW_DESTINATIONS.reduce((s, k) => s + at(dest[k], tEnd), 0)
    if (tot > 0) {
      const share = unfilled / tot
      add(
        'hiring_channel',
        'Displacement runs through hiring, not layoffs',
        `Of ${(tot / 1e6).toFixed(1)}M jobs below baseline in ${region} by ${qEnd}, ${Math.round(100 * share)}% are entry positions not refilled after normal attrition and ${Math.round(100 * (1 - share))}% are separations of incumbents.`,
        'Employers first absorb the fall in labor demand through net occupational attrition (P.63, 2.5%/quarter); layoffs occur only when the required contraction outruns attrition and layoff friction (P.64) (spec §5.3).',
        confOf(doc, 'employment_pct_vs_baseline', qEnd),
        0.3 + 0.6 * Math.abs(share - 0.5) * 2 * (share < 0.5 ? 0.5 : 1),
        { unfilled_entry_cum: unfilled, total_cum: tot, unfilled_share: Number(share.toFixed(3)) },
      )
    }
  }

  const torn = [...(doc.tornado?.employment_pct_vs_baseline ?? [])].sort(
    (a, b) => tornadoSwing(b) - tornadoSwing(a),
  )
  if (torn.length >= 2) {
    const [top, second] = torn as [TornadoRow, TornadoRow]
    const ratio = tornadoSwing(top) / Math.max(tornadoSwing(second), 1e-9)
    const flips = torn.filter(tornadoFlips)
    add(
      'dominant_parameter',
      `${top.name} dominates the employment uncertainty`,
      `Across its literature range (${top.low}–${top.high}), ${top.name} (${top.param}) moves ${qEnd} employment from ${sgn(top.effect_at_low)} to ${sgn(top.effect_at_high)}, a swing ${ratio.toFixed(1)}× the next parameter (${second.name}, ${tornadoSwing(second).toFixed(1)} pp).` +
        (tornadoFlips(top)
          ? ` It is one of ${flips.length} parameter(s) that can flip the sign of the effect.`
          : ''),
      'One-at-a-time sensitivity at the central draw (spec §9.3); the demand feedback (spec §6.2) enters through the multiplier m (P.87) and elasticity η_s (P.60).',
      ratio > 2 ? 'high' : 'medium',
      0.25 + Math.min(0.5, (ratio - 1) / 4) + (tornadoFlips(top) ? 0.2 : 0),
      {
        param: top.param,
        swing_pp: tornadoSwing(top),
        next_param: second.param,
        next_swing_pp: tornadoSwing(second),
        flip_params: flips.map((r) => r.param),
      },
    )
  }

  const regions = doc.meta.regions ?? []
  if (regions.length > 1) {
    const emps = regions
      .filter((x) => doc.series[x])
      .map((x) => [x, at(doc.series[x]?.employment_pct_vs_baseline, tEnd)] as const)
    if (emps.length) {
      const lo = emps.reduce((a, b) => (b[1] < a[1] ? b : a))
      const hi = emps.reduce((a, b) => (b[1] > a[1] ? b : a))
      add(
        'regional_divergence',
        'Regions diverge on employment',
        `The ${qEnd} employment effect ranges from ${sgn(lo[1])} (${lo[0]}) to ${sgn(hi[1])} (${hi[0]}).`,
        'Wage tiers change the profitability test (spec §3.3): lower-wage regions automate later at a given price; access lags and spillover shift timing (spec §4.2, §6.3).',
        'medium',
        0.25 + Math.min(0.5, (hi[1] - lo[1]) / 8),
        {
          employment_pct_by_region: Object.fromEntries(
            emps.map(([k, v]) => [k, Number(v.toFixed(2))]),
          ),
        },
      )
    }
  }

  const conf = doc.confidence?.employment_pct_vs_baseline?.[qEnd]
  if (conf)
    add(
      'sign_confidence',
      `Sign of the employment effect is ${conf.level} confidence`,
      `The ${qEnd} employment sign holds in ${Math.round(100 * conf.sign_share)}% of draws; mechanism cells ${conf.cells_agree ? 'agree' : 'disagree'}` +
        (conf.flip_params.length
          ? `; parameters able to flip it: ${conf.flip_params.join(', ')}.`
          : '.'),
      'Confidence classification combines the draw sign share, cell agreement, and tornado sign flips (spec §9.4).',
      conf.level,
      0.2 + (conf.level === 'low' ? 0.5 : conf.level === 'medium' ? 0.2 : 0),
      { sign_share: conf.sign_share, cells_agree: conf.cells_agree, flip_params: conf.flip_params },
    )

  out.sort((a, b) => b.surprise - a.surprise)
  return out
}

export function mockInsights(doc: ResultsDocument | null, region = 'US', n = 3): InsightsResponse {
  const candidates = doc ? candidateInsights(doc, region) : []
  return {
    scenario_hash: doc?.meta.scenario_hash ?? '',
    scenario_id: doc?.meta.scenario_id ?? null,
    region,
    top: candidates.slice(0, Math.max(1, Math.min(n, 10))),
    candidates,
    method:
      'mock: client-side port of the deterministic ranking by surprise score (subset of candidates)',
  }
}

const ORDER = [
  ['employment_pct_vs_baseline', 'Employment', '%'],
  ['gdp_pct_vs_baseline', 'GDP', '%'],
  ['real_wage_pct_vs_baseline', 'Real wages', '%'],
  ['wage_share_pp_vs_baseline', 'Wage share', ' pp'],
] as const

/** A compact Markdown brief with the same section order as api/aiwsim_api/brief.py. */
export function mockBriefMarkdown(
  doc: ResultsDocument,
  region = 'US',
  compare: ResultsDocument | null = null,
): string {
  const m = doc.meta
  const q = m.quarters
  const tEnd = q.length - 1
  const i30 = Math.max(0, q.indexOf('2030Q4')) || tEnd
  const blk = seriesFor(doc, region) ?? doc.series.US
  const L: string[] = []
  L.push(`# ${m.scenario_id} — AI workforce brief`, '')
  L.push(
    `Region: **${region}** · Horizon: ${q[0]}–${q[tEnd]} · Run: \`${m.scenario_hash}\` · Spec ${m.spec_version} · ${m.draws} Monte Carlo draws, ensemble \`${m.ensemble}\` · Generated ${m.run_at} (mock mode: client-side brief)`,
    '',
  )
  L.push(
    'All effects are relative to a frozen-AI counterfactual (no frontier AI after 2023). Brackets are the 10th–90th percentile across draws; the point value is the median draw.',
    '',
  )
  L.push(
    '## Headline effects',
    '',
    `| Metric | ${q[i30]} | ${q[tEnd]} | Sign confidence (${q[tEnd]}) |`,
    '|---|---|---|---|',
  )
  const cell = (s: Series | undefined, t: number, unit: string) =>
    s?.p10 && s.p90
      ? `${sgn(at(s, t), 1, unit)} [${sgn(at(s, t, 'p10'), 1, unit)}, ${sgn(at(s, t, 'p90'), 1, unit)}]`
      : sgn(at(s, t), 1, unit)
  for (const [k, label, unit] of ORDER) {
    const s = blk?.[k]
    if (s)
      L.push(
        `| ${label} | ${cell(s, i30, unit)} | ${cell(s, tEnd, unit)} | ${confOf(doc, k, q[tEnd] ?? '')} |`,
      )
  }
  L.push('', '## What changed vs the parent scenario', '')
  const diff = doc.explain.diff ?? []
  if (diff.length) {
    L.push('| Lever | From | To | Mechanism |', '|---|---|---|---|')
    for (const d of diff)
      L.push(
        `| \`${d.path}\` | ${JSON.stringify(d.from ?? null)} | ${JSON.stringify(d.to ?? null)} | ${d.mechanism} |`,
      )
  } else L.push('No lever differs from the parent (this is a baseline or preset run).')
  L.push('')
  if (compare) {
    const b = seriesFor(compare, region) ?? compare.series.US
    L.push(
      `## Paired comparison: ${compare.meta.scenario_id} → ${m.scenario_id}`,
      '',
      `| Metric | Δ ${q[i30]} | Δ ${q[tEnd]} |`,
      '|---|---|---|',
    )
    for (const [k, label] of ORDER) {
      const sa = blk?.[k]
      const sb = b?.[k]
      if (sa && sb)
        L.push(
          `| ${label} | ${sgn(at(sa, i30) - at(sb, i30), 1, ' pp')} | ${sgn(at(sa, tEnd) - at(sb, tEnd), 1, ' pp')} |`,
        )
    }
    L.push('', 'Mock mode: medians differenced client-side, no paired draws.', '')
  }
  L.push('## Findings', '')
  for (const c of candidateInsights(doc, region).slice(0, 3)) {
    L.push(
      `**${c.title}.** ${c.statement}`,
      '',
      `*Mechanism:* ${c.mechanism} *Confidence:* ${c.confidence}.`,
      '',
    )
  }
  L.push('## Model notes for this run', '')
  for (const n of doc.explain.notes) L.push(`- ${n}`)
  L.push('')
  const torn = [...(doc.tornado?.employment_pct_vs_baseline ?? [])]
    .sort((a, b) => tornadoSwing(b) - tornadoSwing(a))
    .slice(0, 6)
  if (torn.length) {
    L.push(
      `## What the ${q[tEnd]} employment effect is most sensitive to`,
      '',
      '| Parameter | Range | Effect at low | Effect at high | Swing (pp) |',
      '|---|---|---|---|---|',
    )
    for (const r of torn)
      L.push(
        `| ${r.name} (${r.param}, ${r.tag}) | ${r.low}–${r.high} | ${sgn(r.effect_at_low)} | ${sgn(r.effect_at_high)} | ${tornadoSwing(r).toFixed(1)}${tornadoFlips(r) ? ' ⚠ flips sign' : ''} |`,
      )
    L.push('')
  }
  L.push('## Method and provenance', '')
  L.push(
    `- Model specification v${m.spec_version} (\`docs/model-spec.md\`), ${m.draws}-draw Monte Carlo, ${m.cells?.length ?? 0}-cell structural ensemble.`,
  )
  L.push(`- Capability units: ${m.capability_units}.`)
  const fixtures = Object.entries(m.data_flags)
    .filter(([, v]) => String(v).toUpperCase().includes('FIXTURE'))
    .map(([k]) => k)
  if (fixtures.length)
    L.push(
      `- Data flagged as FIXTURE (structural placeholders pending ingestion): ${fixtures.join(', ')}.`,
    )
  L.push(
    `- Run hash \`${m.scenario_hash}\`; mock data generated by web/scripts/make-mock.ts, not a model run.`,
    '',
  )
  return L.join('\n')
}

/** Self-contained HTML around a rendered brief (mock mode's stand-in for GET /api/brief?format=html). */
export function briefHtml(markdown: string, title: string): string {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
:root{color-scheme:light dark;--ink:#0b0b0b;--muted:#6f6d67;--grid:#e1e0d9;--page:#fcfcfb}
@media(prefers-color-scheme:dark){:root{--ink:#fff;--muted:#a09e97;--grid:#2c2c2a;--page:#1a1a19}}
body{margin:0 auto;max-width:860px;padding:32px 24px;font:15px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:var(--ink);background:var(--page)}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:14px}th,td{border-bottom:1px solid var(--grid);padding:6px 8px;text-align:left;vertical-align:top}
th{font-weight:600}code{font-size:13px;background:rgba(127,127,127,.15);padding:1px 5px;border-radius:4px}.md-h{margin:22px 0 6px;font-size:17px}
p,li{max-width:72ch}@media print{body{padding:0}}
</style></head><body>${renderMarkdown(markdown)}</body></html>`
}
