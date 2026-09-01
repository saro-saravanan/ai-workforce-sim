import { format as d3format } from 'd3'

const f1 = d3format('+.1f')
const f2 = d3format('+.2f')
const compact = d3format('.3~s')
const int = d3format(',.0f')

/** "+0.0" / "−0.0" -> "0.0" (d3-format emits a Unicode minus). */
function noSignedZero(s: string): string {
  return /^[+\u2212-]0(\.0+)?$/.test(s) ? s.slice(1) : s
}

/** "2029Q3" -> "2029 Q3" */
export function quarterLabel(q: string | undefined): string {
  if (!q) return ''
  const m = /^(\d{4})Q([1-4])$/.exec(q)
  return m ? `${m[1]} Q${m[2]}` : q
}

export function quarterYear(q: string): number {
  return Number(q.slice(0, 4))
}

/** Signed percent with 1 decimal, e.g. "-2.1%" */
export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return noSignedZero(digits === 2 ? f2(v) : f1(v)) + '%'
}

/** Signed percentage points, e.g. "-1.8 pp" */
export function fmtPp(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return noSignedZero(f1(v)) + ' pp'
}

/** Unsigned share as percent, e.g. 0.62 -> "62%" */
export function fmtShare(v: number | null | undefined, digits = 0): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return (v * 100).toFixed(digits) + '%'
}

/** Compact count: 1284 -> "1.28k", 1_500_000 -> "1.5M" */
export function fmtCompact(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return compact(v).replace('G', 'B')
}

export function fmtInt(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return int(v)
}

export function fmtUsd(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return '$' + int(v)
}

export function fmtBand(
  lo: number | undefined,
  hi: number | undefined,
  fmt: (v: number) => string,
) {
  if (lo == null || hi == null) return ''
  return `[${fmt(lo)}, ${fmt(hi)}]`
}
