/** The Story view rendered from the mock story document (contracts §26). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { ResultsDocument } from '@/types/results'
import type { StoryDocument } from '@/types/story'
import resultsJson from '@/mock/results.json'
import storyJson from '@/mock/story.json'
import { signedCount } from '@/lib/story'
import { pyFixed, pySigned } from '@/lib/plain'
import { fmtBn } from '@/lib/format'

const story = storyJson as unknown as StoryDocument
const { fetchStory } = vi.hoisted(() => ({
  fetchStory: vi.fn<(doc: ResultsDocument, region: string) => Promise<StoryDocument>>(),
}))

vi.mock('@/api/client', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api/client')>()
  return { ...mod, fetchStory, execBriefUrl: () => null }
})

import StoryView from '@/views/StoryView.vue'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'

async function mountStory() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/story', component: StoryView },
      { path: '/outlook', component: { template: '<div />' } },
    ],
  })
  await router.push('/story?region=US')
  await router.isReady()
  const results = useResultsStore()
  results.doc = structuredClone(resultsJson) as unknown as ResultsDocument
  results.scenarios = [
    { id: 'baseline', name: 'Consensus central', parent: null, description: '' },
    {
      id: 'preset-seba-rethinkx',
      name: 'Preset: Seba / RethinkX disruption',
      parent: 'baseline',
      description: '',
      preset: true,
    },
  ]
  useRegionStore().setRegion('US')
  const w = mount(StoryView, { global: { plugins: [router] } })
  await flushPromises()
  return { w, results }
}

describe('StoryView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchStory.mockReset()
    fetchStory.mockImplementation(async () => structuredClone(story))
    // jsdom has no matchMedia; the theme store reads it for the system preference
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener: () => {} }))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('renders the header, the reconciliation callout and the seven beats in order', async () => {
    const { w } = await mountStory()
    expect(fetchStory).toHaveBeenCalledTimes(1)
    expect(fetchStory.mock.calls[0]?.[1]).toBe('US')
    expect(w.find('h2').text()).toContain('what AI does to work in United States')
    expect(w.text()).toContain('One set of numbers')
    expect(w.text()).toContain(story.numbers.reconciliation.slice(0, 60))
    const beats = w.findAll('[data-beat]').map((el) => el.attributes('data-beat'))
    expect(beats).toEqual(['jobs', 'hiring', 'young', 'pay', 'waves', 'money', 'futures'])
    const titles = w.findAll('[data-beat] h3 .title').map((el) => el.text())
    expect(titles).toEqual(story.beats.map((b) => b.title))
    for (const b of story.beats) {
      expect(w.text()).toContain(b.sentence.slice(0, 40))
      expect(w.text()).toContain(b.what_changes_it.slice(0, 30))
    }
  })

  it('fills the sureness dots per beat', async () => {
    const { w } = await mountStory()
    const filled = (id: string) => w.find(`[data-beat="${id}"]`).findAll('.dot.on').length
    expect(filled('jobs')).toBe(2)
    expect(filled('hiring')).toBe(3)
    expect(filled('futures')).toBe(1)
    expect(w.find('[data-beat="jobs"]').text()).toContain('leaning this way')
    expect(w.find('[data-beat="hiring"]').text()).toContain('we would bet on it')
    expect(w.find('[data-beat="jobs"]').findAll('.dot')).toHaveLength(3)
  })

  it('draws a chart of the right kind under each beat', async () => {
    const { w } = await mountStory()
    expect(w.find('[data-beat="jobs"] .fan').exists()).toBe(true)
    expect(w.find('[data-beat="hiring"] .story-bars').exists()).toBe(true)
    // the age beat carries reference bars and a unit
    const young = w.find('[data-beat="young"]')
    expect(young.findAll('.story-bars rect[rx="1"]')).toHaveLength(4)
    expect(young.text()).toContain('% of jobs lost')
    expect(w.find('[data-beat="waves"] .timeline').exists()).toBe(true)
    expect(w.findAll('[data-beat="waves"] .timeline circle').length).toBeGreaterThan(5)
    expect(w.find('[data-beat="money"]').findAll('svg text.name')).toHaveLength(10)
    expect(w.findAll('[data-beat="futures"] .future')).toHaveLength(3)
  })

  it('offers to open the scenario-run future and selects it in the results store', async () => {
    const { w, results } = await mountStory()
    const btn = w.find('[data-beat="futures"] .future.run button')
    expect(btn.text()).toBe('Open this scenario')
    await btn.trigger('click')
    expect(results.scenarioId).toBe('preset-seba-rethinkx')
  })

  it('renders the policy cards with their stats and the validity ribbon', async () => {
    const { w } = await mountStory()
    const cards = w.findAll('.policy')
    expect(cards).toHaveLength(4)
    expect(cards.map((c) => c.find('h4').text())).toEqual(story.policies.map((p) => p.name))
    const flagged = story.policies.filter((p) => p.validity_note)
    expect(w.findAll('.policy .ribbon')).toHaveLength(flagged.length)
    expect(flagged.length).toBeGreaterThan(0)
    expect(w.find('.policy .ribbon').text()).toBe(flagged[0]!.validity_note)
    const ubi = story.policies.findIndex((p) => p.scenario_id === 'policy-ubi-ai-tax')
    const ubiCard = cards[ubi]!
    const ubiPolicy = story.policies[ubi]!
    expect(ubiCard.text()).toContain(ubiPolicy.sentence)
    expect(ubiCard.text()).toContain(`Jobs${signedCount(ubiPolicy.jobs_delta)}`)
    expect(ubiCard.text()).toContain(`Unemployed${signedCount(ubiPolicy.unemployed_delta)}`)
    expect(ubiCard.text()).toContain(`Cost${fmtBn(ubiPolicy.cost_bn_per_year)} a year`)
    const week = story.policies.findIndex((p) => p.scenario_id === 'policy-work-week-36')
    expect(cards[week]!.text()).toContain(
      `Pay per head${pySigned(story.policies[week]!.real_wage_delta_pp, 1)} points`,
    )
    expect(cards[week]!.text()).toContain('Costnone')
    expect(w.text()).toContain(`Policy runs are read against: ${story.policies_against}`)
  })

  it('says when policy runs are not available', async () => {
    fetchStory.mockImplementationOnce(async () => ({ ...structuredClone(story), policies: [] }))
    const { w } = await mountStory()
    expect(w.text()).toContain('Policy runs are not available for this run')
  })

  it('renders the forecast scoreboard with verdict chips, proxies and preset links', async () => {
    const { w } = await mountStory()
    const rows = w.findAll('table.forecasts tbody tr')
    expect(rows).toHaveLength(story.forecasts.length)
    story.forecasts.forEach((f, i) => {
      const row = rows[i]!
      expect(row.find('td').text()).toBe(f.short)
      expect(row.find('td').attributes('title')).toBe(f.source)
      const claimed = pyFixed(f.claimed, Number.isInteger(f.claimed) ? 0 : 1)
      expect(row.text()).toContain(`${claimed} ${f.unit} by ${f.year} (${f.region})`)
      expect(row.text()).toContain(f.model_central != null ? pyFixed(f.model_central, 1) : 'n/a')
      expect(row.find('.chip').text()).toBe(f.verdict)
      expect(row.find('.chip').classes()).toContain(f.verdict === 'within band' ? 'within' : 'off')
      expect(row.find('.star').exists()).toBe(!!f.proxy)
      expect(row.find('.link-btn').exists()).toBe(!!f.preset_id)
    })
    const seba = rows.find((r) => r.find('.link-btn').exists())!
    expect(seba.find('.link-btn').text()).toBe('run their assumptions')
    expect(story.forecasts.some((f) => f.proxy)).toBe(true)
    expect(w.text()).toContain('nearest model quantity')
  })

  it('lists the caveats and the glossary', async () => {
    const { w } = await mountStory()
    for (const c of story.caveats) expect(w.text()).toContain(c.slice(0, 40))
    expect(w.findAll('.glossary dt').map((d) => d.text())).toEqual(Object.keys(story.glossary))
  })
})
