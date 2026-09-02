/**
 * Helpers for the Applications panel (spec v0.3 §A.6.4, contracts §20): gate positions on a
 * 2024–2040 axis, the region fallback, the per-region displacement table and the U.S. mean wage
 * the cost-per-hour figures are compared with. Pure functions so they are unit-testable.
 */
import type {
  ApplicationEntry,
  ApplicationGate,
  ApplicationRegion,
  OccupationResult,
} from '@/types/results'
import { APPLICATION_GATES } from '@/types/results'

export const GATE_LABELS: Record<ApplicationGate, string> = {
  displacement_1pct: '1% displaced',
  displacement_10pct: '10% displaced',
  coverage_50pct: '50% coverage',
}

/** Short glyph labels for the gate markers, in the same order as APPLICATION_GATES. */
export const GATE_SHORT: Record<ApplicationGate, string> = {
  displacement_1pct: '1%',
  displacement_10pct: '10%',
  coverage_50pct: '½',
}

export const APPLICATION_FAMILY_LABELS: Record<string, string> = {
  embodied: 'Embodied',
  output: 'Output substitution',
  software: 'Software tasks',
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

/** The three gate markers for a region block; missing gates are pinned to x = 1 ("not by 2040"). */
export function gateMarkers(
  first: Partial<Record<ApplicationGate, string | null>> | undefined,
  start = 2024,
  end = 2041,
): GateMarker[] {
  return APPLICATION_GATES.map((gate) => {
    const quarter = first?.[gate] ?? null
    const x = quarterPosition(quarter, start, end)
    return {
      gate,
      label: GATE_LABELS[gate],
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
