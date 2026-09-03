/** The Backtest view rendered from a synthetic results document carrying `backtest` (contracts §29). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import type { BacktestSection, ResultsDocument } from '@/types/results'
import resultsJson from '@/mock/results.json'
import BacktestView from '@/views/BacktestView.vue'
import { useResultsStore } from '@/stores/results'
import { fetchBacktest } from '@/api/client'

const row = (
  series_id: string,
  label: string,
  quarter: string,
  value: number,
  unit: string,
  model_metric: string,
  used_in_fit: 0 | 1,
  model_central: number | null,
  source = 'a source',
): BacktestSection['rows'][number] => {
  const error = model_central == null ? null : Number((model_central - value).toFixed(2))
  return {
    series_id,
    label,
    quarter,
    value,
    unit,
    model_metric,
    source,
    source_tag: `verified: ${source}`,
    used_in_fit,
    model_central,
    error,
    error_pct: error == null ? null : Number(((100 * error) / value).toFixed(1)),
    note: model_metric === 'hyperscaler_capex_bn' ? 'input path, not a prediction' : '',
  }
}

/** Three series: a fitted one, a scored comparison, and a context series the model does not track. */
export const FIXTURE: BacktestSection = {
  horizon: ['2024Q1', '2026Q2'],
  rows: [
    row(
      'btos_firm',
      'Firms using AI (BTOS, %)',
      '2024Q1',
      5.4,
      '% of firms',
      'adoption_share_firm_weighted',
      1,
      8.0,
      'Census BTOS',
    ),
    row(
      'btos_firm',
      'Firms using AI (BTOS, %)',
      '2025Q4',
      17.3,
      '% of firms',
      'adoption_share_firm_weighted',
      1,
      11.8,
      'Census BTOS',
    ),
    row(
      'capex',
      'Hyperscaler capex ($bn/yr)',
      '2024Q4',
      250.7,
      '$bn/yr',
      'hyperscaler_capex_bn',
      0,
      240.0,
      'company reports',
    ),
    row(
      'capex',
      'Hyperscaler capex ($bn/yr)',
      '2025Q4',
      413.4,
      '$bn/yr',
      'hyperscaler_capex_bn',
      0,
      450.0,
      'company reports',
    ),
    row(
      'grad_unemployment',
      'Recent-graduate unemployment (%)',
      '2025Q2',
      4.8,
      '%',
      'none',
      0,
      null,
      'NY Fed',
    ),
    row(
      'grad_unemployment',
      'Recent-graduate unemployment (%)',
      '2026Q2',
      5.6,
      '%',
      'none',
      0,
      null,
      'NY Fed',
    ),
  ],
  summary: {
    btos_firm: {
      label: 'Firms using AI (BTOS, %)',
      n: 2,
      mape_pct: 39.9,
      bias_pct: 8.2,
      used_in_fit: true,
    },
    capex: {
      label: 'Hyperscaler capex ($bn/yr)',
      n: 2,
      mape_pct: 6.6,
      bias_pct: 2.3,
      used_in_fit: false,
    },
    grad_unemployment: {
      label: 'Recent-graduate unemployment (%)',
      n: 0,
      mape_pct: null,
      bias_pct: null,
      used_in_fit: false,
      note: 'not tracked by the model',
    },
  },
  notes: [
    'Central run. Rows marked used_in_fit set a parameter, so their errors are not evidence.',
  ],
}

async function mountView(backtest: BacktestSection | Record<string, never> | null | undefined) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/backtest', component: BacktestView },
      { path: '/story', component: { template: '<div />' } },
    ],
  })
  await router.push('/backtest?region=US')
  await router.isReady()
  const results = useResultsStore()
  const doc = structuredClone(resultsJson) as unknown as ResultsDocument
  if (backtest !== undefined) doc.backtest = backtest
  results.doc = doc
  const w = mount(BacktestView, { global: { plugins: [router] } })
  await flushPromises()
  return w
}

describe('BacktestView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener: () => {} }))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('renders the header sentence, one card per series and the calibration-target badge', async () => {
    const w = await mountView(FIXTURE)
    expect(w.find('h2').text()).toContain('How the model has done against what has happened so far')
    expect(w.find('h2').text()).toContain('2024 to mid-2026')
    expect(w.text()).toContain('not evidence')
    const cards = w.findAll('.series')
    expect(cards.map((c) => c.attributes('data-series'))).toEqual([
      'btos_firm',
      'capex',
      'grad_unemployment',
    ])
    const btos = cards[0]!
    expect(btos.find('h3').text()).toBe('Firms using AI (BTOS, %)')
    expect(btos.find('.series-head .chip.target').exists()).toBe(true)
    expect(btos.text()).toContain('MAPE39.9%')
    expect(btos.text()).toContain('Bias+8%')
    expect(btos.text()).toContain(
      'off by 40% on average over 2 observations; runs 8% above the observations',
    )
    const capex = cards[1]!
    expect(capex.find('.series-head .chip.target').exists()).toBe(false)
    expect(capex.text()).toContain('MAPE6.6%')
    const grad = cards[2]!
    expect(grad.classes()).toContain('context')
    expect(grad.find('.stats').exists()).toBe(false)
    expect(grad.text()).toContain('not tracked by the model')
  })

  it('draws observed and model marks for tracked series and observed points only for context series', async () => {
    const w = await mountView(FIXTURE)
    const btos = w.find('[data-series="btos_firm"]')
    expect(btos.findAll('circle.observed')).toHaveLength(2)
    expect(btos.findAll('rect.model')).toHaveLength(2)
    expect(btos.find('.legend').text()).toContain('model, central run')
    const grad = w.find('[data-series="grad_unemployment"]')
    expect(grad.findAll('circle.observed')).toHaveLength(2)
    expect(grad.findAll('rect.model')).toHaveLength(0)
    expect(grad.find('.legend').text()).toContain('observed only')
    expect(grad.find('.legend .unit').text()).toBe('%')
  })

  it('tables every observation with the source tag as the title and the notes', async () => {
    const w = await mountView(FIXTURE)
    const rows = w.findAll('table.rows tbody tr')
    expect(rows).toHaveLength(FIXTURE.rows.length)
    const first = rows[0]!
    expect(first.text()).toContain('Firms using AI (BTOS, %)')
    expect(first.find('.chip.target').exists()).toBe(true)
    expect(first.text()).toContain('2024 Q1')
    expect(first.text()).toContain('5.4')
    expect(first.text()).toContain('8.0')
    expect(first.text()).toContain('+48%')
    expect(first.find('td.source').attributes('title')).toBe('verified: Census BTOS')
    expect(first.find('td.source').text()).toBe('Census BTOS')
    const capex = rows[2]!
    expect(capex.find('.chip.target').exists()).toBe(false)
    expect(capex.find('.star').exists()).toBe(true)
    const grad = rows[4]!
    expect(grad.text()).toContain('—')
    expect(w.text()).toContain(FIXTURE.notes[0]!)
  })

  it('says so when the run carries no backtest (the mock, an empty section)', async () => {
    for (const bt of [undefined, null, {}] as const) {
      setActivePinia(createPinia())
      const w = await mountView(bt)
      expect(w.text()).toContain('No backtest section in this run')
      expect(w.findAll('.series')).toHaveLength(0)
      w.unmount()
    }
  })

  it('fetchBacktest reads the document section and answers null for anything else', () => {
    const doc = structuredClone(resultsJson) as unknown as ResultsDocument
    expect(fetchBacktest(doc)).toBeNull()
    expect(fetchBacktest(null)).toBeNull()
    doc.backtest = {}
    expect(fetchBacktest(doc)).toBeNull()
    doc.backtest = FIXTURE
    expect(fetchBacktest(doc)).toBe(FIXTURE)
  })
})
