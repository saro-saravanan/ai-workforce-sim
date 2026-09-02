import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { ResultsDocument } from '@/types/results'
import type { ChatResponse } from '@/types/chat'

type Api = typeof import('@/api/client')
vi.mock('@/api/client', () => ({
  USE_MOCK: false,
  USE_STATIC: false,
  fetchChatStatus: vi.fn<Api['fetchChatStatus']>(async () => ({
    available: true,
    model: 'test-model',
  })),
  sendChat: vi.fn<Api['sendChat']>(),
  runScenarioDoc: vi.fn<Api['runScenarioDoc']>(),
  runScenario: vi.fn<Api['runScenario']>(),
  compareRuns: vi.fn<Api['compareRuns']>(async () => ({
    diff: [],
    delta: { series: {}, states: [], occupations: [] },
    confidence: {},
  })),
  fetchScenarios: vi.fn<Api['fetchScenarios']>(async () => []),
  fetchLevers: vi.fn<Api['fetchLevers']>(async () => []),
  fetchScenario: vi.fn<Api['fetchScenario']>(async () => {
    throw new Error('no scenario')
  }),
}))

import * as api from '@/api/client'
import { useChatStore } from '@/stores/chat'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'
import { useScrubberStore } from '@/stores/scrubber'
import { useToastStore } from '@/stores/toast'

function doc(id: string, hash: string): ResultsDocument {
  const s = { p50: [0, -1, -2] }
  return {
    meta: {
      spec_version: '0.2',
      schema_version: '0.3',
      scenario_id: id,
      scenario_hash: hash,
      seed: 1,
      run_at: '',
      draws: 1,
      ensemble: 'all',
      quarters: ['2024Q1', '2030Q4', '2040Q4'],
      regions: ['US'],
      baseline: 'frozen',
      data_flags: { occ_state: 'real', occ_sector: 'real', aei_anchoring: 'real' },
      capability_units: 'doublings',
    },
    series: {
      US: {
        gdp_pct_vs_baseline: s,
        employment_pct_vs_baseline: s,
        real_wage_pct_vs_baseline: s,
        nominal_wage_pct_vs_baseline: s,
        wage_share_pp_vs_baseline: s,
        tfp_pct_vs_baseline: s,
        price_index_pct_vs_baseline: s,
        displaced_workers_cum: s,
        adoption_share: s,
        ai_spend_bn: s,
        capability_index: s,
        capability_horizon_hours: s,
      },
    },
    occupations: [],
    states: [],
    channels: {},
    explain: { notes: [] },
  }
}

const reply = (extra: Partial<ChatResponse> = {}): ChatResponse => ({
  reply: 'ok',
  tool_calls: [],
  proposed_scenario: null,
  proposals: [],
  runs: [],
  usage: { input_tokens: 1, output_tokens: 1 },
  model: 'test-model',
  stop_reason: 'end_turn',
  ...extra,
})

const proposal = {
  proposal_id: 'prop-1',
  parent: 'baseline',
  rationale: 'faster clock',
  diff: [{ path: 'levers.capability.doubling_months', from: 5, to: 4, mechanism: 'clock' }],
  scenario: {
    schema_version: '0.2' as const,
    id: 'fast-4mo',
    name: 'Faster capability',
    parent: 'baseline',
    levers: { capability: { doubling_months: 4 } },
  },
}

describe('chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.sendChat).mockReset()
    vi.mocked(api.runScenarioDoc).mockReset()
  })

  it('builds the context from the results, region and scrubber stores', () => {
    const results = useResultsStore()
    const region = useRegionStore()
    const scrubber = useScrubberStore()
    const chat = useChatStore()
    results.doc = doc('baseline', 'sha256:a')
    scrubber.setLength(3)
    scrubber.set(1)
    chat.view = 'economy'
    // World has no series block on the server: the U.S. is the reference region
    expect(chat.context).toEqual({
      scenario_hash: 'sha256:a',
      scenario_id: 'baseline',
      compare_hash: undefined,
      compare_id: undefined,
      region: 'US',
      quarter: '2030Q4',
      view: 'economy',
    })
    region.setRegion('EU')
    expect(chat.context.region).toBe('EU')
  })

  it('loads the status and sends the visible transcript with mode and context', async () => {
    const results = useResultsStore()
    const chat = useChatStore()
    results.doc = doc('baseline', 'sha256:a')
    await chat.loadStatus()
    expect(chat.available).toBe(true)
    vi.mocked(api.sendChat).mockResolvedValueOnce(reply({ reply: 'first' }))
    await chat.send('hello', 'insights')
    const [body] = vi.mocked(api.sendChat).mock.calls[0]!
    expect(body.mode).toBe('insights')
    expect(body.messages).toEqual([{ role: 'user', content: 'hello' }])
    expect(body.context.scenario_hash).toBe('sha256:a')
    expect(body.confirmed_proposals).toEqual([])
    expect(chat.messages.map((m) => [m.role, m.content])).toEqual([
      ['user', 'hello'],
      ['assistant', 'first'],
    ])
    expect(chat.pending).toBe(false)
  })

  it('records an error on the assistant turn, toasts, and drops it from the next transcript', async () => {
    const chat = useChatStore()
    const toast = useToastStore()
    vi.mocked(api.sendChat).mockRejectedValueOnce(new Error('502 backend'))
    await chat.send('hi')
    expect(chat.error).toBe('502 backend')
    expect(chat.messages[1]!.error).toBe('502 backend')
    expect(toast.toasts.some((t) => t.text.includes('502 backend'))).toBe(true)
    expect(chat.transcript()).toEqual([{ role: 'user', content: 'hi' }])
  })

  it('confirm runs the proposal as the compare scenario and the next request carries it', async () => {
    const results = useResultsStore()
    const chat = useChatStore()
    results.doc = doc('baseline', 'sha256:a')
    vi.mocked(api.sendChat).mockResolvedValueOnce(
      reply({ proposed_scenario: proposal, proposals: [proposal] }),
    )
    await chat.send('what if capability doubles every 4 months')
    const m = chat.messages[1]!
    expect(m.proposal?.proposal_id).toBe('prop-1')

    const run = doc('fast-4mo', 'sha256:run1')
    vi.mocked(api.runScenarioDoc).mockResolvedValueOnce(run)
    const ran = await chat.confirm('prop-1')
    expect(api.runScenarioDoc).toHaveBeenCalledWith(proposal.scenario)
    expect(ran).toEqual({ scenario_hash: 'sha256:run1', scenario_id: 'fast-4mo', as: 'compare' })
    expect(results.compareId).toBe('sha256:run1')
    expect(results.docB?.meta.scenario_hash).toBe('sha256:run1')
    expect(results.doc?.meta.scenario_hash).toBe('sha256:a')
    expect(api.compareRuns).toHaveBeenCalled()
    expect(results.scenarios.find((s) => s.id === 'sha256:run1')?.name).toBe('Faster capability')
    expect(chat.confirmedProposals).toEqual(['prop-1'])
    expect(m.running).toBe(false)

    vi.mocked(api.sendChat).mockResolvedValueOnce(reply())
    await chat.send('now compare them')
    const [body] = vi.mocked(api.sendChat).mock.calls[1]!
    expect(body.confirmed_proposals).toEqual(['prop-1'])
    expect(body.context.compare_hash).toBe('sha256:run1')
    expect(body.context.compare_id).toBe('sha256:run1')
    expect(body.messages).toHaveLength(3)
  })

  it('confirm becomes the current run when nothing is loaded, and can be switched later', async () => {
    const results = useResultsStore()
    const chat = useChatStore()
    vi.mocked(api.sendChat).mockResolvedValueOnce(
      reply({ proposed_scenario: proposal, proposals: [proposal] }),
    )
    await chat.send('what if')
    vi.mocked(api.runScenarioDoc).mockResolvedValueOnce(doc('fast-4mo', 'sha256:run1'))
    const ran = await chat.confirm('prop-1')
    expect(ran?.as).toBe('current')
    expect(results.scenarioId).toBe('fast-4mo')
    expect(results.doc?.meta.scenario_hash).toBe('sha256:run1')
    expect(results.scenarioDoc?.id).toBe('fast-4mo')
    // switching slots re-uses the kept document; no second run
    await chat.confirm('prop-1', 'compare')
    expect(api.runScenarioDoc).toHaveBeenCalledTimes(1)
    expect(results.compareId).toBe('sha256:run1')
  })

  it('confirm reports a failed run without marking the proposal confirmed', async () => {
    const results = useResultsStore()
    const chat = useChatStore()
    results.doc = doc('baseline', 'sha256:a')
    vi.mocked(api.sendChat).mockResolvedValueOnce(
      reply({ proposed_scenario: proposal, proposals: [proposal] }),
    )
    await chat.send('what if')
    vi.mocked(api.runScenarioDoc).mockRejectedValueOnce(new Error('engine down'))
    expect(await chat.confirm('prop-1')).toBeNull()
    expect(chat.confirmedProposals).toEqual([])
    expect(chat.error).toContain('engine down')
    expect(results.compareId).toBeNull()
  })

  it('caps the transcript sent at 40 turns', async () => {
    const chat = useChatStore()
    for (let i = 0; i < 25; i++) {
      vi.mocked(api.sendChat).mockResolvedValueOnce(reply({ reply: `r${i}` }))
      await chat.send(`q${i}`)
    }
    expect(chat.messages).toHaveLength(50)
    expect(chat.transcript()).toHaveLength(40)
    expect(chat.transcript()[0]).toEqual({ role: 'user', content: 'q5' })
  })
})
