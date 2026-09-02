import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type {
  ResultsDocument,
  ScenarioSummary,
  ScenarioDocument,
  StatesGeoJSON,
  NationalMetric,
  Series,
  LeverDef,
  CompareResponse,
  HeadlineMetric,
} from '@/types/results'
import * as api from '@/api/client'
import { useToastStore } from '@/stores/toast'

export const useResultsStore = defineStore('results', () => {
  const doc = shallowRef<ResultsDocument | null>(null)
  const geo = shallowRef<StatesGeoJSON | null>(null)
  const scenarios = ref<ScenarioSummary[]>([])
  const scenarioId = ref('baseline')
  /** the canonical (resolved) scenario document of the current run, for the levers form */
  const scenarioDoc = shallowRef<ScenarioDocument | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ----- compare (Phase 2) -----
  /** scenario id of B; `compare=` in the URL */
  const compareId = ref<string | null>(null)
  const docB = shallowRef<ResultsDocument | null>(null)
  const compare = shallowRef<CompareResponse | null>(null)
  const compareLoading = ref(false)

  // ----- levers (Phase 2) -----
  const levers = shallowRef<LeverDef[]>([])

  const quarters = computed(() => doc.value?.meta.quarters ?? [])
  const meta = computed(() => doc.value?.meta ?? null)
  const series = computed(() => doc.value?.series.US ?? null)
  const occupations = computed(() => doc.value?.occupations ?? [])
  const states = computed(() => doc.value?.states ?? [])
  const channels = computed(() => doc.value?.channels ?? {})
  const notes = computed(() => doc.value?.explain.notes ?? [])
  const diff = computed(() => doc.value?.explain.diff ?? [])
  const trace = computed(() => doc.value?.explain.trace ?? {})
  const structural = computed(() => doc.value?.structural ?? {})
  const confidence = computed(() => doc.value?.confidence ?? {})
  const tornado = computed(() => doc.value?.tornado ?? {})
  const cohorts = computed(() => doc.value?.cohorts ?? null)
  const flows = computed(() => doc.value?.flows ?? null)
  const isFixture = computed(() => doc.value?.meta.data_flags.occ_state === 'FIXTURE')
  const isMock = api.USE_MOCK
  const scenarioName = computed(
    () => scenarios.value.find((s) => s.id === scenarioId.value)?.name ?? scenarioId.value,
  )
  const compareName = computed(() =>
    compareId.value
      ? (scenarios.value.find((s) => s.id === compareId.value)?.name ?? compareId.value)
      : null,
  )

  function national(metric: NationalMetric): Series | undefined {
    return series.value?.[metric]
  }
  function confidenceAt(metric: HeadlineMetric, quarter: string) {
    return confidence.value[metric]?.[quarter]
  }

  async function loadScenarios() {
    try {
      scenarios.value = await api.fetchScenarios()
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function loadLevers() {
    if (levers.value.length) return
    try {
      levers.value = await api.fetchLevers()
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

  async function loadScenarioDoc(id: string) {
    try {
      scenarioDoc.value = await api.fetchScenario(id)
    } catch {
      scenarioDoc.value = null
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
      void loadScenarioDoc(id)
      if (compareId.value) void loadCompare()
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  /** Runs a what-if child scenario and switches the app to it. */
  async function runChild(child: ScenarioDocument) {
    loading.value = true
    error.value = null
    const toast = useToastStore()
    try {
      const next = await api.runScenarioDoc(child)
      doc.value = next
      scenarioId.value = child.id
      scenarioDoc.value = child
      if (!scenarios.value.some((s) => s.id === child.id))
        scenarios.value = [
          ...scenarios.value,
          { id: child.id, name: child.name, parent: child.parent, description: child.description ?? '', user: true },
        ]
      if (isMock)
        toast.push(`Mock mode: "${child.name}" re-used the parent's results (no engine).`, 'warn')
      else toast.push(`Ran ${child.name} (${next.meta.draws} draws).`)
      if (compareId.value) void loadCompare()
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function saveScenario(child: ScenarioDocument) {
    const toast = useToastStore()
    try {
      const saved = await api.saveScenario(child)
      if (!scenarios.value.some((s) => s.id === saved.id))
        scenarios.value = [
          ...scenarios.value,
          { id: saved.id, name: saved.name, parent: saved.parent, description: saved.description ?? '', user: true },
        ]
      toast.push(isMock ? `Mock mode: saved "${saved.name}" for this session.` : `Saved ${saved.id}.`)
      return saved
    } catch (e) {
      error.value = (e as Error).message
      return null
    }
  }

  /** Loads scenario B and the paired comparison against the current document. */
  async function loadCompare() {
    const b = compareId.value
    const a = doc.value
    if (!b || !a) {
      docB.value = null
      compare.value = null
      return
    }
    compareLoading.value = true
    try {
      const next = docB.value?.meta.scenario_id === b ? docB.value : await api.runScenario(b)
      docB.value = next
      compare.value = await api.compareRuns(a, next)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      compareLoading.value = false
    }
  }

  function setCompare(id: string | null) {
    if (id === scenarioId.value) id = null
    if (compareId.value === id) return
    compareId.value = id
    if (id) void loadCompare()
    else {
      docB.value = null
      compare.value = null
    }
  }

  return {
    doc,
    geo,
    scenarios,
    scenarioId,
    scenarioDoc,
    scenarioName,
    loading,
    error,
    compareId,
    compareName,
    docB,
    compare,
    compareLoading,
    levers,
    quarters,
    meta,
    series,
    occupations,
    states,
    channels,
    notes,
    diff,
    trace,
    structural,
    confidence,
    tornado,
    cohorts,
    flows,
    isFixture,
    isMock,
    national,
    confidenceAt,
    loadScenarios,
    loadLevers,
    loadGeo,
    loadScenarioDoc,
    runScenario,
    runChild,
    saveScenario,
    loadCompare,
    setCompare,
  }
})
