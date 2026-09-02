/** The client-side outlook (contracts §27): a port of `outlook()` in api/aiwsim_api/story.py. */
import { describe, expect, it } from 'vitest'
import type { OccupationResult, ResultsDocument, Series } from '@/types/results'
import type { StoryBeat } from '@/types/story'
import resultsJson from '@/mock/results.json'
import { outlookDetail, outlookFromDoc } from '../outlook'
import { millions, pyFixed, pyGrouped, pyRound, pySigned } from '../plain'

const quarters = ['2024Q1', '2030Q4', '2040Q4']
const s = (v: number, spread = 1): Series => ({
  p50: [0, v / 2, v],
  p10: [0, v / 2 - spread, v - spread],
  p90: [0, v / 2 + spread, v + spread],
  central: [0, v / 2, v],
})
function occ(
  code: string,
  emp2040: number,
  o: Partial<OccupationResult> & { sw?: number; emb?: number } = {},
): OccupationResult {
  const { sw = 0.2, emb, ...rest } = o
  return {
    occ_code: code,
    title: `Occupation ${code}`,
    cluster_id: 'c',
    major_group: '11',
    emp0: 100_000,
    wage0: 50_000,
    automatable_share: 0.5,
    exposure_beta: 0.5,
    displacement: { p50: [0, sw / 2, sw], central: [0, sw / 2, sw] },
    displacement_embodied: emb == null ? undefined : { central: [0, emb / 2, emb] },
    employment_pct_vs_baseline: s(emp2040),
    real_wage_pct_vs_baseline: s(2),
    ...rest,
  }
}
/** eleven occupations, 2040 effects −10 … 0, so rank percentiles fall exactly on 0, 10, …, 100 */
function doc(extra: OccupationResult[] = []): ResultsDocument {
  const occupations = Array.from({ length: 11 }, (_, i) => occ(`o${i}`, -10 + i))
  return {
    meta: { quarters },
    occupations: [...occupations, ...extra],
    cohorts: {
      age: [
        { band: '16-24', employment_pct_vs_baseline: s(-4), share_of_jobs_lost: s(0.46) },
        { band: '55+', employment_pct_vs_baseline: s(-0.2), share_of_jobs_lost: s(0.03) },
      ],
      education: [],
      income_decile: [],
    },
  } as unknown as ResultsDocument
}

describe('verdict by rank percentile (10 / 30 / 70 / 90)', () => {
  const d = doc()
  const verdict = (code: string) => outlookDetail(d, code, null).occupation?.verdict
  it.each([
    ['o0', 0, 'among the hardest hit'],
    ['o1', 10, 'harder hit than most'],
    ['o2', 20, 'harder hit than most'],
    ['o3', 30, 'about average'],
    ['o6', 60, 'about average'],
    ['o7', 70, 'less affected than most'],
    ['o8', 80, 'less affected than most'],
    ['o9', 90, 'among the most protected'],
    ['o10', 100, 'among the most protected'],
  ])('%s at the %i th percentile is "%s"', (code, pct, expected) => {
    const card = outlookDetail(d, code, null).occupation!
    expect(card.rank_percentile).toBe(pct)
    expect(verdict(code)).toBe(expected)
  })
})

describe('the how rule', () => {
  it('is software when software displacement is at least twice the embodied share', () => {
    const d = doc([occ('x', -3, { sw: 0.3, emb: 0.15 }), occ('y', -3, { sw: 0.3 })])
    expect(outlookDetail(d, 'x', null).occupation?.how).toBe(
      'mostly software doing parts of the job',
    )
    expect(outlookDetail(d, 'y', null).occupation?.how).toBe(
      'mostly software doing parts of the job',
    )
    expect(outlookDetail(d, 'y', null).occupation?.task_hours_automated_2040).toEqual({
      software: 30,
      machines: 0,
    })
  })
  it('is machines when the embodied share is larger, a mix in between', () => {
    const d = doc([occ('x', -3, { sw: 0.1, emb: 0.3 }), occ('y', -3, { sw: 0.3, emb: 0.2 })])
    expect(outlookDetail(d, 'x', null).occupation?.how).toBe('mostly machines and vehicles')
    expect(outlookDetail(d, 'y', null).occupation?.how).toBe('a mix of software and machines')
    expect(outlookDetail(d, 'y', null).occupation?.sentence).toContain(
      "A mix of software and machines: 50% of the work's task-hours are done by AI by 2040.",
    )
  })
})

describe('growing nearby and the sentences', () => {
  it('lists up to three others of the same major group with 50,000+ workers, best first', () => {
    const d = doc([
      occ('big', -1, { major_group: '99', emp0: 60_000 }),
      occ('small', 5, { major_group: '99', emp0: 49_999 }),
      occ('a', 2, { major_group: '99', emp0: 50_000 }),
      occ('b', 1, { major_group: '99', emp0: 80_000 }),
      occ('c', 3, { major_group: '99', emp0: 80_000 }),
      occ('d', 0.5, { major_group: '99', emp0: 80_000 }),
    ])
    const card = outlookDetail(d, 'big', null).occupation!
    expect(card.growing_nearby).toEqual([
      ['Occupation c', 3],
      ['Occupation a', 2],
      ['Occupation b', 1],
    ])
  })
  it('writes the occupation sentence with the server wording', () => {
    const card = outlookDetail(doc(), 'o1', null).occupation!
    expect(card.employment_pct_2030).toBe(-4.5)
    expect(card.range_2040).toEqual([-10, -8])
    expect(card.sentence).toBe(
      "Occupation o1: harder hit than most. About 9% fewer jobs than there would have been by 2040 (4% by 2030); likely between -10% and -8%. Mostly software doing parts of the job: 20% of the work's task-hours are done by AI by 2040. Pay for those who stay is +2% in real terms.",
    )
  })
  it('writes the age sentences, with the entry-risk line for the youngest band', () => {
    const young = outlookDetail(doc(), null, '16-24').age!
    expect(young.share_of_jobs_lost).toBe(0.46)
    expect(young.sentence).toBe(
      "People under 25 carry 46% of the jobs that go missing by 2040, about 4.0% of the group's jobs. Most of the loss is jobs never offered rather than jobs taken away, so the practical risk is at entry: first jobs, changing jobs, returning to work.",
    )
    const old = outlookDetail(doc(), null, '55+').age!
    expect(old.sentence).toMatch(
      /^People 55 and over carry 3% .* about 0\.2% of the group's jobs\. Incumbents are mostly protected/,
    )
    expect(outlookDetail(doc(), null, '25-44').age).toBeUndefined()
  })
  it('assembles the response with the three beats, the legend and the region note', () => {
    const beats = ['jobs', 'hiring', 'young', 'pay', 'waves'].map((id) => ({ id }) as StoryBeat)
    const us = outlookFromDoc(doc(), 'o0', null, 'US', beats)
    expect(us.beats.map((b) => b.id)).toEqual(['jobs', 'hiring', 'pay'])
    expect(us.note).toBe('')
    expect(us.sureness_legend.high).toEqual(['we would bet on it', 3])
    expect(us.occupation?.occ_code).toBe('o0')
    expect(us.age).toBeUndefined()
    const eu = outlookFromDoc(doc(), null, null, 'EU')
    expect(eu.note).toMatch(/U\.S\. detail/)
    expect(eu.beats).toEqual([])
    expect(eu.occupation).toBeUndefined()
  })
})

describe('against the mock results document', () => {
  it('describes taxi drivers (53-3054) in task-hours', () => {
    const d = resultsJson as unknown as ResultsDocument
    const card = outlookDetail(d, '53-3054', '16-24').occupation!
    expect(card.title).toBe('Taxi drivers and chauffeurs')
    expect(card.sentence).toContain('task-hours')
    expect(card.sentence).toMatch(
      /^Taxi drivers and chauffeurs: (among the hardest hit|harder hit than most|about average|less affected than most|among the most protected)\./,
    )
    expect(card.rank_percentile).toBeGreaterThanOrEqual(0)
    expect(card.rank_percentile).toBeLessThanOrEqual(100)
    expect(card.growing_nearby.length).toBeLessThanOrEqual(3)
    for (const [, v] of card.growing_nearby) expect(Number.isFinite(v)).toBe(true)
  })
})

describe('python number formatting', () => {
  it('rounds exact ties to even like f-strings', () => {
    expect(pyFixed(2.5)).toBe('2')
    expect(pyFixed(3.5)).toBe('4')
    expect(pyFixed(-2.5)).toBe('-2')
    expect(pyFixed(0.25, 1)).toBe('0.2')
    expect(pyFixed(4.65, 1)).toBe('4.7')
    expect(pyFixed(1.23456, 2)).toBe('1.23')
    expect(pySigned(3.2)).toBe('+3')
    expect(pySigned(-3.2)).toBe('-3')
    expect(pyRound(0.5)).toBe(0)
    expect(pyRound(1.5)).toBe(2)
    expect(pyGrouped(2495.4)).toBe('2,495')
  })
  it('writes counts in words', () => {
    expect(millions(8_588_865)).toBe('8.6 million')
    expect(millions(-22_904_712)).toBe('22.9 million')
    expect(millions(175_575)).toBe('176,000')
    expect(millions(42.4)).toBe('42')
  })
})
