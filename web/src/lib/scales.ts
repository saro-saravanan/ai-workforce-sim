import {
  scaleDiverging,
  scaleSequential,
  scaleSqrt,
  scaleOrdinal,
  interpolateLab,
  piecewise,
  extent,
  max,
} from 'd3'
import { ALL_PAIRS_CAP, CATEGORICAL, DIVERGING, NEUTRAL, SEQUENTIAL, type Mode } from './palette'

/** Symmetric domain around zero so the neutral midpoint always means "no change". */
export function symmetricDomain(values: Iterable<number | null | undefined>): [number, number] {
  let m = 0
  for (const v of values) if (v != null && Number.isFinite(v)) m = Math.max(m, Math.abs(v))
  if (m === 0) m = 1
  return [-m, m]
}

/** Nice-round the half-range so legend ticks read as clean numbers. */
export function niceSymmetric(domain: [number, number]): [number, number] {
  const m = Math.max(Math.abs(domain[0]), Math.abs(domain[1]))
  if (m === 0) return [-1, 1]
  const p = Math.pow(10, Math.floor(Math.log10(m)))
  const f = m / p
  const nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10
  return [-nf * p, nf * p]
}

/** Diverging color scale centered at 0; negative = red arm, positive = blue arm. */
export function divergingScale(domain: [number, number], mode: Mode) {
  const { neg, mid, pos } = DIVERGING[mode]
  const interp = piecewise(interpolateLab, [neg, mid, pos])
  return scaleDiverging<string>(interp).domain([domain[0], 0, domain[1]]).clamp(true)
}

/** Sequential one-hue scale for magnitudes (displaced workers etc.). */
export function sequentialScale(
  domain: [number, number],
  mode: Mode,
  hue: 'blue' | 'red' = 'blue',
) {
  const [lo, hi] = SEQUENTIAL[mode][hue]
  return scaleSequential<string>(interpolateLab(lo, hi)).domain(domain).clamp(true)
}

export function magnitudeDomain(values: Iterable<number | null | undefined>): [number, number] {
  const vals = Array.from(values).filter((v): v is number => v != null && Number.isFinite(v))
  const m = max(vals) ?? 1
  return [0, m === 0 ? 1 : m]
}

/** Radius ∝ sqrt(employment); returns a scale with the given max radius in px. */
export function radiusScale(emps: Iterable<number>, maxR = 26) {
  const [, hi] = extent(Array.from(emps)) as [number, number]
  return scaleSqrt()
    .domain([0, hi || 1])
    .range([3, maxR])
}

/**
 * Categorical colors for an all-pairs form (scatter): the first `cap` keys (in the order given)
 * get slots 1..cap; every other key folds to the neutral gray.
 */
export function cappedCategorical(keys: string[], mode: Mode, cap = ALL_PAIRS_CAP) {
  const kept = keys.slice(0, cap)
  const scale = scaleOrdinal<string, string>()
    .domain(kept)
    .range(CATEGORICAL[mode].slice(0, kept.length))
    .unknown(NEUTRAL[mode])
  return { scale, kept, other: NEUTRAL[mode] }
}

/** Categorical colors for an adjacent form (stack): up to 8 fixed-order slots. */
export function stackCategorical(keys: string[], mode: Mode) {
  const kept = keys.slice(0, 8)
  return scaleOrdinal<string, string>()
    .domain(kept)
    .range(CATEGORICAL[mode].slice(0, kept.length))
    .unknown(NEUTRAL[mode])
}

/** Relative luminance-based ink choice for text placed inside a fill. */
export function inkOn(hex: string): '#0b0b0b' | '#ffffff' {
  const n = parseInt(hex.replace('#', ''), 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  const lin = (c: number) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  const L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  return L > 0.4 ? '#0b0b0b' : '#ffffff'
}
