import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type {
  ResultsDocument,
  ScenarioSummary,
  StatesGeoJSON,
  NationalMetric,
  Series,
} from '@/types/results'
import * as api from '@/api/client'

export const useResultsStore = defineStore('results', () => {
  const doc = shallowRef<ResultsDocument | null>(null)
  const geo = shallowRef<StatesGeoJSON | null>(null)
  const scenarios = ref<ScenarioSummary[]>([])
  const scenarioId = ref('baseline')
  const loading = ref(false)
  const error = ref<string | null>(null)

  const quarters = computed(() => doc.value?.meta.quarters ?? [])
  const meta = computed(() => doc.value?.meta ?? null)
  const series = computed(() => doc.value?.series.US ?? null)
  const occupations = computed(() => doc.value?.occupations ?? [])
  const states = computed(() => doc.value?.states ?? [])
  const channels = computed(() => doc.value?.channels ?? {})
  const notes = computed(() => doc.value?.explain.notes ?? [])
  const isFixture = computed(() => doc.value?.meta.data_flags.occ_state === 'FIXTURE')
  const isMock = api.USE_MOCK

  function national(metric: NationalMetric): Series | undefined {
    return series.value?.[metric]
  }

  async function loadScenarios() {
    try {
      scenarios.value = await api.fetchScenarios()
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function loadGeo() {
    if (geo.value) return
    try {
      geo.value = await api.fetchStatesGeo()
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  /** Runs (or fetches the cached run of) a scenario and swaps the results document in. */
  async function runScenario(id: string) {
    loading.value = true
    error.value = null
    try {
      const next = await api.runScenario(id)
      doc.value = next
      scenarioId.value = id
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return {
    doc,
    geo,
    scenarios,
    scenarioId,
    loading,
    error,
    quarters,
    meta,
    series,
    occupations,
    states,
    channels,
    notes,
    isFixture,
    isMock,
    national,
    loadScenarios,
    loadGeo,
    runScenario,
  }
})
