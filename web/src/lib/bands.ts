import { area as d3area, line as d3line, type ScaleLinear } from 'd3'
import type { Series } from '@/types/results'

export type Scale = ScaleLinear<number, number>

/** Fill opacities for the two nested bands; drawn stacked so 25–75 reads darker. */
export const BAND_OUTER_OPACITY = 0.12
export const BAND_INNER_OPACITY = 0.2

export function hasOuterBand(s: Series) {
  return !!(s.p10 && s.p90)
}
export function hasInnerBand(s: Series) {
  return !!(s.p25 && s.p75)
}
/** `central` is drawn only when it differs from p50 somewhere. */
export function hasCentral(s: Series) {
  return !!s.central && s.central.some((v, i) => Math.abs(v - (s.p50[i] ?? v)) > 1e-9)
}

/** Every value that drives the y-domain: all percentiles and central. */
export function seriesExtentValues(s: Series): number[] {
  return [
    ...s.p50,
    ...(s.p10 ?? []),
    ...(s.p25 ?? []),
    ...(s.p75 ?? []),
    ...(s.p90 ?? []),
    ...(s.central ?? []),
  ].filter((v) => Number.isFinite(v))
}

export function linePath(values: number[], x: Scale, y: Scale): string {
  return (
    d3line<number>()
      .defined((d) => Number.isFinite(d))
      .x((_, i) => x(i))
      .y((d) => y(d))(values) ?? ''
  )
}

export function bandPath(lo: number[], hi: number[], x: Scale, y: Scale): string {
  const n = Math.min(lo.length, hi.length)
  return (
    d3area<number>()
      .x((_, i) => x(i))
      .y0((_, i) => y(lo[i] ?? 0))
      .y1((_, i) => y(hi[i] ?? 0))(Array.from({ length: n }, (_, i) => i)) ?? ''
  )
}

/** Tooltip rows for one index of a series. */
export function bandRows(
  s: Series,
  i: number,
  label: string,
  format: (v: number) => string,
  swatch: string,
) {
  const rows: Array<{ label: string; value: string; swatch?: string; kind?: 'line' | 'rect' }> = []
  const v = s.p50[i]
  rows.push({ label: `${label} (median)`, value: v == null ? '—' : format(v), swatch, kind: 'line' })
  if (s.p25 && s.p75)
    rows.push({
      label: '25–75 band',
      value: `${format(s.p25[i] ?? 0)} to ${format(s.p75[i] ?? 0)}`,
      swatch,
      kind: 'rect',
    })
  if (s.p10 && s.p90)
    rows.push({
      label: '10–90 band',
      value: `${format(s.p10[i] ?? 0)} to ${format(s.p90[i] ?? 0)}`,
      swatch,
      kind: 'rect',
    })
  if (hasCentral(s) && s.central?.[i] != null)
    rows.push({ label: 'Central run', value: format(s.central[i]!) })
  return rows
}
