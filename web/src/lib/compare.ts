/**
 * Paired-difference helpers for the compare view.
 * The API (`/api/compare`) pairs draws by seed and returns exact percentiles of B − A.
 * In mock mode we only have marginal percentiles of A and B, so the delta band is derived
 * under an assumed draw correlation: var(d) = σA² + σB² − 2ρσAσB with σ ≈ (p90 − p10) / 2.5631.
 */
import type {
  CompareResponse,
  Confidence,
  HeadlineMetric,
  NationalMetric,
  ResultsDocument,
  Series,
} from '@/types/results'
import { HEADLINE_METRICS } from '@/types/results'
import { seriesFor } from '@/lib/world'

/** z(0.9) − z(0.1) */
const Z_RANGE = 2.5631
/** z(0.9) */
const Z90 = 1.2816

export const DEFAULT_RHO = 0.8

export interface DeltaSeries {
  p10: number[]
  p50: number[]
  p90: number[]
}

/** Element-wise B − A of the medians, with an approximate paired band. */
export function pairedDeltaSeries(a: Series, b: Series, rho = DEFAULT_RHO): DeltaSeries {
  const n = Math.min(a.p50.length, b.p50.length)
  const p50: number[] = []
  const p10: number[] = []
  const p90: number[] = []
  for (let i = 0; i < n; i++) {
    const d = (b.p50[i] ?? 0) - (a.p50[i] ?? 0)
    const sa = a.p10 && a.p90 ? ((a.p90[i] ?? 0) - (a.p10[i] ?? 0)) / Z_RANGE : 0
    const sb = b.p10 && b.p90 ? ((b.p90[i] ?? 0) - (b.p10[i] ?? 0)) / Z_RANGE : 0
    const varD = Math.max(0, sa * sa + sb * sb - 2 * rho * sa * sb)
    const half = Z90 * Math.sqrt(varD)
    p50.push(d)
    p10.push(d - half)
    p90.push(d + half)
  }
  return { p10, p50, p90 }
}

/** Sign-agreement share of a delta band at one quarter (used for the mock confidence). */
export function deltaSignShare(d: DeltaSeries, i: number): number {
  const lo = d.p10[i] ?? 0
  const hi = d.p90[i] ?? 0
  const mid = d.p50[i] ?? 0
  if (hi === lo) return 1
  // fraction of a normal with p10=lo, p90=hi on the median's side of zero
  const sigma = (hi - lo) / Z_RANGE
  const z = Math.abs(mid) / (sigma || 1e-9)
  return Math.min(1, Math.max(0.5, 0.5 + 0.5 * erf(z / Math.SQRT2)))
}

function erf(x: number): number {
  // Abramowitz–Stegun 7.1.26
  const s = Math.sign(x)
  const ax = Math.abs(x)
  const t = 1 / (1 + 0.3275911 * ax)
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) *
      t *
      Math.exp(-ax * ax)
  return s * y
}

export function confidenceFromShare(share: number, cellsAgree: boolean, flip: string[]): Confidence {
  const level = share >= 0.9 && cellsAgree && flip.length === 0 ? 'high' : share >= 0.7 && cellsAgree ? 'medium' : 'low'
  return { level, sign_share: Number(share.toFixed(3)), cells_agree: cellsAgree, flip_params: flip }
}

/** Mock of GET /api/compare?a&b from two full documents, for one region selection ('world' aggregates). */
export function pairedCompare(
  a: ResultsDocument,
  b: ResultsDocument,
  region = 'US',
  rho = DEFAULT_RHO,
): CompareResponse {
  const series: CompareResponse['delta']['series'] = {}
  const A = seriesFor(a, region)
  const B = seriesFor(b, region)
  if (A && B) {
    for (const k of Object.keys(A) as NationalMetric[]) {
      const sa = A[k]
      const sb = B[k]
      // Phase 6 blocks also carry scalars (self_employed_fte_2024) and per-class maps (fleet_stock)
      if (sa && sb && typeof sa === 'object' && typeof sb === 'object' && 'p50' in sa && 'p50' in sb)
        series[k] = pairedDeltaSeries(sa, sb, rho)
    }
  }
  const aStates = new Map(a.states.map((s) => [s.fips, s]))
  const states = b.states
    .filter((s) => aStates.has(s.fips))
    .map((s) => ({
      fips: s.fips,
      employment_pct_vs_baseline: {
        p50: pairedDeltaSeries(
          aStates.get(s.fips)!.employment_pct_vs_baseline,
          s.employment_pct_vs_baseline,
          rho,
        ).p50,
      },
    }))
  const aOcc = new Map(a.occupations.map((o) => [o.occ_code, o]))
  const occupations = b.occupations
    .filter((o) => aOcc.has(o.occ_code))
    .map((o) => ({
      occ_code: o.occ_code,
      displacement: {
        p50: pairedDeltaSeries(aOcc.get(o.occ_code)!.displacement, o.displacement, rho).p50,
      },
    }))
  const confidence: CompareResponse['confidence'] = {}
  const refs = ['2030Q4', '2040Q4'].map((q) => [q, a.meta.quarters.indexOf(q)] as const)
  for (const m of HEADLINE_METRICS as HeadlineMetric[]) {
    const d = series[m]
    if (!d) continue
    const per: Record<string, Confidence> = {}
    for (const [qk, qi] of refs) {
      if (qi < 0) continue
      const share = deltaSignShare(d as DeltaSeries, qi)
      const cellsAgree = (a.confidence?.[m]?.[qk]?.cells_agree ?? true) && (b.confidence?.[m]?.[qk]?.cells_agree ?? true)
      const flip = [...new Set([...(a.confidence?.[m]?.[qk]?.flip_params ?? []), ...(b.confidence?.[m]?.[qk]?.flip_params ?? [])])]
      per[qk] = confidenceFromShare(share, cellsAgree, flip)
    }
    confidence[m] = per
  }
  // the diff is B's canonical diff vs its parent when A is that parent; else both sides' diffs
  const diff = b.meta.scenario_id !== a.meta.scenario_id ? (b.explain.diff ?? []) : []
  return { diff, delta: { series, states, occupations }, confidence }
}
