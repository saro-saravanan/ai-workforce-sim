/** The scoreboard's Phase 9 marks: calibration targets, claim ranges and the footer count (contracts §29). */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { ForecastRow } from '@/types/results'
import ForecastTable from '@/components/story/ForecastTable.vue'

const base: ForecastRow = {
  source: 'Goldman Sachs Global Investment Research, 2023',
  short: 'Goldman Sachs 2023',
  region: 'US',
  year: 2033,
  metric: 'gdp_pct',
  proxy: 0,
  preset_id: null,
  claimed: 7,
  unit: '% GDP',
  note: 'a 7% rise in global GDP over ten years',
  quarter: '2033Q4',
  model_central: 6.1,
  model_p10: 2.4,
  model_p90: 9.8,
  verdict: 'within band',
}

describe('ForecastTable', () => {
  it('marks calibration targets with a muted chip and counts them apart from comparisons', () => {
    const rows: ForecastRow[] = [
      { ...base, role: 'comparison' },
      {
        ...base,
        short: 'Challenger 2025',
        role: 'target',
        claimed: 54836,
        unit: 'cuts',
        metric: 'ai_layoffs_in_year',
      },
      { ...base, short: 'Acemoglu 2024' },
    ]
    const w = mount(ForecastTable, { props: { forecasts: rows } })
    const trs = w.findAll('tbody tr')
    expect(trs).toHaveLength(3)
    expect(trs[0]!.find('.chip.target').exists()).toBe(false)
    const chip = trs[1]!.find('td .chip.target')
    expect(chip.exists()).toBe(true)
    expect(chip.text()).toBe('calibration target')
    expect(chip.attributes('title')).toContain('not evidence')
    expect(trs[1]!.find('td').text()).toContain('Challenger 2025')
    // a row without a role is a comparison
    expect(trs[2]!.find('.chip.target').exists()).toBe(false)
    expect(w.find('.counts').text()).toBe(
      '2 comparisons, 1 calibration target (used to set a parameter; not evidence).',
    )
  })

  it('shows the claim range after the claimed value when the source gives one', () => {
    const rows: ForecastRow[] = [
      { ...base, claimed_low: 5.5, claimed_high: 8.5 },
      { ...base, short: 'IMF 2024', claimed_low: null, claimed_high: null },
    ]
    const w = mount(ForecastTable, { props: { forecasts: rows } })
    const trs = w.findAll('tbody tr')
    expect(trs[0]!.find('td.claim').text()).toBe('7 (5.5 to 8.5) % GDP by 2033 (US)')
    expect(trs[1]!.find('td.claim').text()).toBe('7 % GDP by 2033 (US)')
    expect(w.find('.counts').text()).toBe('2 comparisons, 0 calibration targets.')
  })

  it('labels the band as the range of the model’s assumptions with the tooltip', () => {
    const w = mount(ForecastTable, { props: { forecasts: [base] } })
    const ths = w.findAll('th')
    const band = ths.find((t) => t.text() === "Range of the model's assumptions")!
    expect(band.exists()).toBe(true)
    expect(band.attributes('title')).toContain('not a forecast interval')
    expect(w.text()).not.toContain('Likely range')
  })
})
