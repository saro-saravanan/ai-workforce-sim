/** Mock mode of the story endpoints (contracts §26–27): the mock story relabelled for the run. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ResultsDocument } from '@/types/results'
import resultsA from '@/mock/results.json'

type Api = typeof import('@/api/client')
let api: Api

beforeEach(async () => {
  vi.stubEnv('VITE_USE_MOCK', '1')
  vi.stubEnv('VITE_STATIC', '')
  vi.resetModules()
  api = await import('@/api/client')
})
afterEach(() => vi.unstubAllEnvs())

function docFor(id: string): ResultsDocument {
  const d = structuredClone(resultsA) as unknown as ResultsDocument
  d.meta.scenario_id = id
  if (id !== 'baseline') d.meta.scenario_hash = `sha256:mock-${id}`
  return d
}

describe('mock story and outlook', () => {
  it('relabels the mock story with the run it is asked for', async () => {
    expect(api.USE_MOCK).toBe(true)
    const base = await api.fetchStory(docFor('baseline'), 'US')
    expect(base.scenario_id).toBe('baseline')
    expect(base.scenario_name).toBe('Baseline: central assumptions')
    expect(base.beats.map((b) => b.id)).toEqual([
      'jobs',
      'hiring',
      'young',
      'pay',
      'waves',
      'money',
      'futures',
    ])
    const seba = await api.fetchStory(docFor('preset-seba-rethinkx'), 'world')
    expect(seba.scenario_hash).toBe('sha256:mock-preset-seba-rethinkx')
    expect(seba.scenario_name).toBeNull()
    expect(seba.policies).toHaveLength(4)
  })

  it('computes the outlook client-side with the story beats', async () => {
    const res = await api.fetchOutlook(docFor('baseline'), '53-3054', '16-24', 'world')
    expect(res.region).toBe('US')
    expect(res.beats.map((b) => b.id)).toEqual(['jobs', 'hiring', 'pay'])
    expect(res.occupation?.title).toBe('Taxi drivers and chauffeurs')
    expect(res.age?.band).toBe('16-24')
    expect(res.note).toBe('')
  })

  it('has no executive brief page (the view builds it client-side)', () => {
    expect(api.execBriefUrl(docFor('baseline'))).toBeNull()
    expect(api.storyRegion('world')).toBe('US')
    expect(api.storyRegion('EU')).toBe('EU')
  })
})
