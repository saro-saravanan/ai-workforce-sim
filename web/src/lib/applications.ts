/**
 * Helpers for the Applications panel (spec v0.3 §A.6.4, contracts §20 and §24): gate positions
 * on a 2024–2040 axis, the region fallback (and the exporter fallback of traded rows), the
 * family grouping, the per-region displacement table, the output-substitution strip and the
 * U.S. mean wage the cost-per-hour figures are compared with. Pure functions so they are
 * unit-testable.
 */
import type {
  ApplicationEntry,
  ApplicationFamily,
  ApplicationGate,
  ApplicationRegion,
  OccupationResult,
  RegionSeries,
  Series,
} from '@/types/results'
import { APPLICATION_FAMILIES, APPLICATION_GATES } from '@/types/results'

export const GATE_LABELS: Record<ApplicationGate, string> = {
  displacement_1pct: '1% displaced',
  displacement_10pct: '10% displaced',
  coverage_50pct: '50% coverage',
}

/**
 * Output rows (contracts §24) read the same three gates on different quantities: the share of
 * the category's human output lost vs baseline, and the AI share of consumption.
 */
export const OUTPUT_GATE_LABELS: Record<ApplicationGate, string> = {
  displacement_1pct: '1% of human output lost',
  displacement_10pct: '10% of human output lost',
  coverage_50pct: 'AI share 50%',
}

export function gateLabels(family?: string): Record<ApplicationGate, string> {
  return family === 'output' ? OUTPUT_GATE_LABELS : GATE_LABELS
}

/** Short glyph labels for the gate markers, in the same order as APPLICATION_GATES. */
export const GATE_SHORT: Record<ApplicationGate, string> = {
  displacement_1pct: '1%',
  displacement_10pct: '10%',
  coverage_50pct: '½',
}

/** Family headers of the panel, in `APPLICATION_FAMILIES` order (contracts §23). */
export const APPLICATION_FAMILY_LABELS: Record<ApplicationFamily | string, string> = {
  embodied: 'Embodied automation',
  output: 'Output substitution',
  traded: 'Traded services',
  software: 'Software applications',
}

/** Column captions per family: what the row's displacement figure and its bar mean. */
export const FAMILY_COLUMNS: Record<
  ApplicationFamily | string,
  { displacement: string; bar: string | null; approval: boolean }
> = {
  embodied: { displacement: 'Displacement share', bar: 'Coverage · approval', approval: true },
  output: { displacement: 'Human output vs baseline', bar: 'AI share', approval: false },
  traded: { displacement: 'Displacement share', bar: null, approval: false },
  software: { displacement: 'Displacement share', bar: null, approval: false },
}

/** Labels of the content categories (`meta.content_categories`, contracts §23). */
export const CONTENT_CATEGORY_LABELS: Record<string, string> = {
  video: 'Video',
  music: 'Music',
  text: 'Text',
  image_design: 'Image and design',
  translation_voice: 'Translation and voice',
  advertising: 'Advertising',
}
export function contentCategoryLabel(id: string): string {
  return CONTENT_CATEGORY_LABELS[id] ?? id.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}

export interface ApplicationGroup {
  family: ApplicationFamily | string
  label: string
  apps: ApplicationEntry[]
}

/**
 * Rows grouped by family in catalogue order (embodied, output, traded, software); families the
 * document does not carry are omitted and unknown families follow in first-seen order. Row order
 * within a family is the document's.
 */
export function groupApplications(apps: ApplicationEntry[]): ApplicationGroup[] {
  const byFamily = new Map<string, ApplicationEntry[]>()
  for (const a of apps) byFamily.set(a.family, [...(byFamily.get(a.family) ?? []), a])
  const order = [
    ...APPLICATION_FAMILIES.filter((f) => byFamily.has(f)),
    ...[...byFamily.keys()].filter((f) => !(APPLICATION_FAMILIES as string[]).includes(f)),
  ]
  return order.map((family) => ({
    family,
    label: APPLICATION_FAMILY_LABELS[family] ?? family,
    apps: byFamily.get(family) ?? [],
  }))
}

/** Reference quarters of the per-region table (contracts §8 reference quarters plus 2035). */
export const TABLE_QUARTERS = ['2030Q4', '2035Q4', '2040Q4'] as const

/**
 * Position of a quarter on a year axis: 2024Q1 → 0 at `start`, the end of 2040Q4 → 1 at
 * `end` (the axis spans `start`…`end` where `end` is the first year past the horizon).
 * Returns null for a malformed or missing quarter.
 */
export function quarterPosition(q: string | null | undefined, start = 2024, end = 2041): number | null {
  if (!q) return null
  const m = /^(\d{4})Q([1-4])$/.exec(q)
  if (!m) return null
  const year = Number(m[1]) + (Number(m[2]) - 1) / 4
  const span = end - start
  if (span <= 0) return null
  return Math.min(1, Math.max(0, (year - start) / span))
}

export interface GateMarker {
  gate: ApplicationGate
  label: string
  short: string
  quarter: string | null
  /** 0..1 along the axis; a missing gate sits at the right edge */
  x: number
  /** true when the gate is not passed by the horizon */
  missing: boolean
}

/**
 * The three gate markers for a region block; missing gates are pinned to x = 1 ("not by 2040").
 * `family` picks the labels (output rows: human output lost, AI share).
 */
export function gateMarkers(
  first: Partial<Record<ApplicationGate, string | null>> | undefined,
  start = 2024,
  end = 2041,
  family?: string,
): GateMarker[] {
  const labels = gateLabels(family)
  return APPLICATION_GATES.map((gate) => {
    const quarter = first?.[gate] ?? null
    const x = quarterPosition(quarter, start, end)
    return {
      gate,
      label: labels[gate],
      short: GATE_SHORT[gate],
      quarter,
      x: x ?? 1,
      missing: x == null,
    }
  })
}

/** Year ticks for the gate axis: every `step` years from `start` up to the last full year. */
export function yearTicks(start = 2024, end = 2041, step = 4): Array<{ year: number; x: number }> {
  const out: Array<{ year: number; x: number }> = []
  for (let y = start; y < end; y += step) out.push({ year: y, x: (y - start) / (end - start) })
  return out
}

/**
 * The region block an application row reads: the selected region when present, else the U.S.
 * (`fallback` says which). World has no application split and reads the U.S. too.
 */
export function applicationRegion(
  app: ApplicationEntry,
  region: string,
): { block: ApplicationRegion | null; region: string; fallback: boolean } {
  const own = region !== 'world' ? app.by_region[region] : undefined
  if (own) return { block: own, region, fallback: false }
  const us = app.by_region.US
  if (us) return { block: us, region: 'US', fallback: true }
  const first = Object.keys(app.by_region)[0]
  return first
    ? { block: app.by_region[first]!, region: first, fallback: true }
    : { block: null, region, fallback: true }
}

/**
 * The exporting region a traded row should show when the selected region has no exposure: the
 * region with the largest `displacement_share` at quarter `q` (ties and an all-zero quarter fall
 * back to the horizon end). Null when no region has any displacement at all.
 */
export function largestExporter(app: ApplicationEntry, q: number): string | null {
  const entries = Object.entries(app.by_region)
  const pick = (i: number) => {
    let best: string | null = null
    let max = 0
    for (const [id, b] of entries) {
      const v = b.displacement_share[i] ?? 0
      if (v > max) {
        max = v
        best = id
      }
    }
    return best
  }
  const n = Math.max(0, ...entries.map(([, b]) => b.displacement_share.length))
  return pick(q) ?? (n ? pick(n - 1) : null)
}

/**
 * Region block for a traded row (contracts §24): the selected region when it has any exposure,
 * else the largest exporter at `q` (`fallback` and `region` say so). Regions without a block
 * behave as in `applicationRegion`.
 */
export function tradedRegion(
  app: ApplicationEntry,
  region: string,
  q: number,
): { block: ApplicationRegion | null; region: string; fallback: boolean; exporter: boolean } {
  const own = region !== 'world' ? app.by_region[region] : undefined
  if (own && own.displacement_share.some((v) => v > 0))
    return { block: own, region, fallback: false, exporter: false }
  const exp = largestExporter(app, q)
  if (exp && exp !== region)
    return { block: app.by_region[exp]!, region: exp, fallback: true, exporter: true }
  return { ...applicationRegion(app, region), exporter: false }
}

/** Displacement share (percent) at the reference quarters for every region in `by_region`. */
export function displacementTable(
  app: ApplicationEntry,
  quarters: string[],
  refs: readonly string[] = TABLE_QUARTERS,
): Array<{ region: string; values: Array<number | null> }> {
  const idx = refs.map((q) => quarters.indexOf(q))
  return Object.entries(app.by_region).map(([region, b]) => ({
    region,
    values: idx.map((i) => (i >= 0 ? (b.displacement_share[i] ?? null) : null)),
  }))
}

/** Employment-weighted mean 2023 wage over the occupations table (U.S., $/yr). */
export function meanWage(occupations: Array<Pick<OccupationResult, 'emp0' | 'wage0'>>): number | null {
  let w = 0
  let sum = 0
  for (const o of occupations) {
    if (!Number.isFinite(o.emp0) || !Number.isFinite(o.wage0) || o.emp0 <= 0) continue
    w += o.emp0
    sum += o.emp0 * o.wage0
  }
  return w > 0 ? sum / w : null
}

/** Annual wage → hourly at a 2,080-hour year (40 h × 52 wk). */
export function hourlyWage(annual: number | null): number | null {
  return annual == null ? null : annual / 2080
}

/** Occupation titles for the target codes; a wildcard (`*manip`) is kept as a note. */
export function targetTitles(
  codes: string[],
  occupations: Array<Pick<OccupationResult, 'occ_code' | 'title'>>,
): Array<{ code: string; title: string | null }> {
  const byCode = new Map(occupations.map((o) => [o.occ_code, o.title]))
  return codes.map((code) => ({
    code,
    title: code.startsWith('*')
      ? `all occupations on the ${code.slice(1)} class`
      : (byCode.get(code) ?? null),
  }))
}

// ---------- Phase 7: the output-substitution strip (contracts §24) ----------

export interface OutputStripTile {
  category: string
  label: string
  /** AI share of consumption at `q`, percent (median) with the 10–90 band when present */
  share: number | null
  shareLo: number | null
  shareHi: number | null
  /** consumption relative to the baseline at `q` (Q/Q0, median) */
  ratio: number | null
  /** the median share path, percent, for the sparkline */
  path: number[]
}

export interface OutputStrip {
  tiles: OutputStripTile[]
  /** AI-content revenue at `q`, $bn per year (median), null when the series is absent */
  revenue: number | null
  revenueLo: number | null
  revenueHi: number | null
  /** consumer-surplus proxy at `q`, $bn per year (median) */
  surplus: number | null
  surplusLo: number | null
  surplusHi: number | null
}

const at = (s: Series | undefined, i: number, k: 'p50' | 'p10' | 'p90' = 'p50'): number | null => {
  const v = s?.[k]?.[i]
  return v == null || !Number.isFinite(v) ? null : v
}

/**
 * One tile per content category (the document's `meta.content_categories`, else the keys of
 * `ai_content_share`) plus the two totals, read from a region's series block at quarter `q`.
 * Null when the block carries no output-substitution series.
 */
export function outputStrip(
  block: Pick<
    RegionSeries,
    'ai_content_share' | 'content_consumption_ratio' | 'ai_content_revenue_bn' | 'consumer_surplus_proxy_bn'
  > | null | undefined,
  q: number,
  categories?: string[],
): OutputStrip | null {
  const shares = block?.ai_content_share
  if (!shares) return null
  const ids = (categories?.length ? categories : Object.keys(shares)).filter((c) => shares[c])
  const tiles = ids.map((c) => {
    const s = shares[c]
    return {
      category: c,
      label: contentCategoryLabel(c),
      share: at(s, q),
      shareLo: at(s, q, 'p10'),
      shareHi: at(s, q, 'p90'),
      ratio: at(block?.content_consumption_ratio?.[c], q),
      path: s?.p50 ?? [],
    }
  })
  const rev = block?.ai_content_revenue_bn
  const sur = block?.consumer_surplus_proxy_bn
  return {
    tiles,
    revenue: at(rev, q),
    revenueLo: at(rev, q, 'p10'),
    revenueHi: at(rev, q, 'p90'),
    surplus: at(sur, q),
    surplusLo: at(sur, q, 'p10'),
    surplusHi: at(sur, q, 'p90'),
  }
}
