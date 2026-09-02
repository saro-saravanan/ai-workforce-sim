/**
 * The personal outlook, computed client-side (static and mock modes) from the results document.
 * A port of `outlook()` in `api/aiwsim_api/story.py` (contracts §27): the same rank thresholds,
 * the same `how` rule, the same "growing nearby" list and the same sentences.
 */
import type { OccupationResult, ResultsDocument } from '@/types/results'
import type { OutlookAge, OutlookOccupation, OutlookResponse, StoryBeat } from '@/types/story'
import { capitalize, millions, pyFixed, pyRound, pySigned } from '@/lib/plain'

export const AGE_BANDS = ['16-24', '25-44', '45-54', '55+'] as const
export type AgeBand = (typeof AGE_BANDS)[number]

export const AGE_LABELS: Record<string, string> = {
  '16-24': 'under 25',
  '25-44': '25 to 44',
  '45-54': '45 to 54',
  '55+': '55 and over',
}

export const SURENESS: Record<string, [string, number]> = {
  high: ['we would bet on it', 3],
  medium: ['leaning this way', 2],
  low: ['a coin flip', 1],
}

export const OUTLOOK_BEATS = ['jobs', 'hiring', 'pay']

export const OUTLOOK_NOTE =
  "Occupation and age figures are U.S. detail; the region's totals are in the beats above."

type SeriesLike = Partial<Record<'p10' | 'p50' | 'p90' | 'central', number[]>> | undefined

/** story.py `_p`: the requested percentile, else p50, else central */
function p(s: SeriesLike, t: number, k: 'p10' | 'p50' | 'p90' | 'central' = 'p50'): number {
  const arr = nonEmpty(s?.[k]) ?? nonEmpty(s?.p50) ?? nonEmpty(s?.central)
  return arr ? Number(arr[t] ?? 0) : 0
}
function nonEmpty(a: number[] | undefined): number[] | undefined {
  return a && a.length ? a : undefined
}

export interface OutlookDetail {
  occupation?: OutlookOccupation
  age?: OutlookAge
}

/** The occupation and age cards for a document (U.S. detail). */
export function outlookDetail(
  doc: ResultsDocument,
  occCode: string | null | undefined,
  ageBand: string | null | undefined,
): OutlookDetail {
  const q = doc.meta.quarters
  const t40 = q.length - 1
  const t30 = q.includes('2030Q4') ? q.indexOf('2030Q4') : t40
  const yr = (q[t40] ?? '').slice(0, 4)
  const occs = doc.occupations ?? []
  const out: OutlookDetail = {}
  const o = occCode ? occs.find((x) => x.occ_code === occCode) : undefined
  if (o) out.occupation = occupationCard(o, occs, t30, t40, yr)
  const ages = doc.cohorts?.age
  if (ageBand && ages?.length) {
    const a = ages.find((x) => x.band === ageBand)
    if (a) {
      const share = p(a.share_of_jobs_lost, t40)
      const own = p(a.employment_pct_vs_baseline, t40)
      out.age = {
        band: ageBand,
        share_of_jobs_lost: share,
        employment_pct_2040: own,
        sentence:
          `People ${AGE_LABELS[ageBand] ?? ageBand} carry ${pyFixed(100 * share)}% of the jobs that go missing by ${yr}, about ${pyFixed(Math.abs(own), 1)}% of the group's jobs. ` +
          (ageBand === '16-24'
            ? 'Most of the loss is jobs never offered rather than jobs taken away, so the practical risk is at entry: first jobs, changing jobs, returning to work.'
            : 'Incumbents are mostly protected because employers cut through attrition rather than layoffs; the risk rises if you change occupations.'),
      }
    }
  }
  return out
}

function occupationCard(
  o: OccupationResult,
  occs: OccupationResult[],
  t30: number,
  t40: number,
  yr: string,
): OutlookOccupation {
  const e30 = p(o.employment_pct_vs_baseline, t30)
  const e40 = p(o.employment_pct_vs_baseline, t40)
  const lo = p(o.employment_pct_vs_baseline, t40, 'p10')
  const hi = p(o.employment_pct_vs_baseline, t40, 'p90')
  const dSw = p(o.displacement, t40, 'central')
  const dEmb = o.displacement_embodied?.central?.length
    ? p(o.displacement_embodied, t40, 'central')
    : 0
  const rw = p(o.real_wage_pct_vs_baseline, t40, 'central')
  const at40 = (x: OccupationResult) => p(x.employment_pct_vs_baseline, t40)
  const ranks = [...occs].sort((a, b) => at40(a) - at40(b))
  const pos = ranks.findIndex((x) => x.occ_code === o.occ_code)
  const pctRank = (100 * pos) / Math.max(ranks.length - 1, 1)
  const same = occs.filter(
    (x) => x.major_group === o.major_group && x.occ_code !== o.occ_code && x.emp0 >= 50_000,
  )
  const growing = [...same].sort((a, b) => at40(b) - at40(a)).slice(0, 3)
  const how =
    dSw >= 2 * Math.max(dEmb, 1e-9)
      ? 'mostly software doing parts of the job'
      : dEmb > dSw
        ? 'mostly machines and vehicles'
        : 'a mix of software and machines'
  const verdict =
    pctRank < 10
      ? 'among the hardest hit'
      : pctRank < 30
        ? 'harder hit than most'
        : pctRank < 70
          ? 'about average'
          : pctRank < 90
            ? 'less affected than most'
            : 'among the most protected'
  return {
    occ_code: o.occ_code,
    title: o.title,
    employment_2024: o.emp0,
    employment_pct_2030: e30,
    employment_pct_2040: e40,
    range_2040: [lo, hi],
    task_hours_automated_2040: { software: dSw * 100, machines: dEmb * 100 },
    real_wage_pct_2040: rw,
    rank_percentile: pyRound(pctRank),
    verdict,
    how,
    growing_nearby: growing.map((x) => [x.title, at40(x)]),
    sentence:
      `${o.title}: ${verdict}. About ${pyFixed(Math.abs(e40))}% ${e40 < 0 ? 'fewer' : 'more'} jobs than there would have been by ${yr} ` +
      `(${pyFixed(Math.abs(e30))}% by 2030); likely between ${pySigned(lo)}% and ${pySigned(hi)}%. ${capitalize(how)}: ${pyFixed(100 * (dSw + dEmb))}% of the work's task-hours are done by AI by ${yr}. ` +
      `Pay for those who stay is ${pySigned(rw)}% in real terms.`,
  }
}

/**
 * The outlook response (contracts §27) for a document: the jobs, hiring and pay beats of its
 * story plus the occupation and age cards.
 */
export function outlookFromDoc(
  doc: ResultsDocument,
  occCode: string | null | undefined,
  ageBand: string | null | undefined,
  region = 'US',
  beats: StoryBeat[] = [],
): OutlookResponse {
  return {
    region,
    beats: beats.filter((b) => OUTLOOK_BEATS.includes(b.id)),
    sureness_legend: SURENESS,
    note: region === 'US' ? '' : OUTLOOK_NOTE,
    ...outlookDetail(doc, occCode, ageBand),
  }
}

/** "8.6 million fewer" / "22.9 million more" for a jobs number (positive = fewer than no AI). */
export function jobsWords(jobs: number): string {
  return `${millions(jobs)} ${jobs > 0 ? 'fewer' : 'more'}`
}
