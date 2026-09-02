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

/** Billions of dollars: 1455 -> "$1.46tn", 60.3 -> "$60bn", 4.2 -> "$4.2bn" */
export function fmtBn(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  const a = Math.abs(v)
  const sign = v < 0 ? '\u2212' : ''
  if (a >= 1000) return `${sign}$${(a / 1000).toFixed(2)}tn`
  if (a >= 100) return `${sign}$${a.toFixed(0)}bn`
  if (a >= 10) return `${sign}$${a.toFixed(1)}bn`
  return `${sign}$${a.toFixed(2)}bn`
}

/** Task horizon in hours -> "12 min", "1.5 h", "3 days", "2 weeks", "4 months" */
export function fmtHorizon(hours: number | null | undefined): string {
  if (hours == null || !Number.isFinite(hours)) return '—'
  if (hours < 1 / 60) return `${Math.max(1, Math.round(hours * 3600))} s`
  if (hours < 1) return `${(hours * 60).toFixed(hours * 60 < 10 ? 1 : 0)} min`
  if (hours < 24) return `${hours.toFixed(hours < 10 ? 1 : 0)} h`
  if (hours < 168) return `${(hours / 24).toFixed(1)} days`
  if (hours < 720) return `${(hours / 168).toFixed(1)} weeks`
  if (hours < 8760) return `${(hours / 720).toFixed(1)} months`
  return `${(hours / 8760).toFixed(1)} years`
}

/** "$/M tokens": 15 -> "$15.00", 0.0043 -> "$0.0043" */
export function fmtUsdPerMtok(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  if (v >= 1) return `$${v.toFixed(2)}`
  if (v >= 0.01) return `$${v.toFixed(3)}`
  return `$${v.toPrecision(2)}`
}
