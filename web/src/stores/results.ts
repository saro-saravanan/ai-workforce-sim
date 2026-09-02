import { defineStore } from 'pinia'
import { computed, ref, shallowRef, watch } from 'vue'
import type {
  ResultsDocument,
  ScenarioSummary,
  ScenarioDocument,
  StatesGeoJSON,
  WorldGeoJSON,
  NationalMetric,
  Series,
  LeverDef,
  CompareResponse,
  HeadlineMetric,
  RegionSeries,
} from '@/types/results'
import * as api from '@/api/client'
import { useToastStore } from '@/stores/toast'
import { useRegionStore } from '@/stores/region'
import { seriesFor } from '@/lib/world'

export const useResultsStore = defineStore('results', () => {
  const regionStore = useRegionStore()
  const doc = shallowRef<ResultsDocument | null>(null)
  const geo = shallowRef<StatesGeoJSON | null>(null)
  const worldGeo = shallowRef<WorldGeoJSON | null>(null)
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

  // ----- child runs of this session (Phase 2 drawer, Phase 4 chat proposals) -----
  /** child scenario documents run this session, by scenario id and by result hash */
  const localDocs = new Map<string, ScenarioDocument>()

  const quarters = computed(() => doc.value?.meta.quarters ?? [])
  const meta = computed(() => doc.value?.meta ?? null)
  // ----- regions (Phase 3) -----
  const regions = computed(() => doc.value?.regions ?? [])
  const world = computed(() => doc.value?.world ?? [])
  const supply = computed(() => doc.value?.supply ?? null)
  /** the region ids present in this run */
  const regionIds = computed(() => doc.value?.meta.regions ?? Object.keys(doc.value?.series ?? {}))
  /** true when the selected region has a series block (or is World) */
  const hasRegion = computed(
    () => regionStore.isWorld || !!doc.value?.series[regionStore.region],
  )
  /**
   * The series block every view reads: `series[region]`, or the client-side World aggregate
   * (lib/world.ts). Falls back to the U.S. when the run has no block for the selected region.
   */
  const series = computed<RegionSeries | null>(() => {
    const d = doc.value
    if (!d) return null
    return seriesFor(d, regionStore.region) ?? d.series.US ?? null
  })
  /** the same selection applied to scenario B */
  const seriesB = computed<RegionSeries | null>(() => {
    const d = docB.value
    if (!d) return null
    return seriesFor(d, regionStore.region) ?? d.series.US ?? null
  })
  const rents = computed(() => series.value?.ai_rents_received_bn ?? null)
  const regionInfo = computed(() =>
    regions.value.find((r) => r.region_id === regionStore.region) ?? null,
  )
  /**
   * The region's occupational composition is imputed (`data_flags.occ_region === 'FIXTURE'`, the
   * structural proxy of contracts §11): drawn hatched on the map. Shared fixtures such as
   * trade_weights apply to every region and are not hatched.
   */
  const isRegionFixture = (id: string) =>
    regions.value.find((r) => r.region_id === id)?.data_flags.occ_region === 'FIXTURE'
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
  /** static demo (contracts §18): precomputed runs, no engine and no chat */
  const isStatic = api.USE_STATIC
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

  async function loadWorldGeo() {
    if (worldGeo.value) return
    try {
      worldGeo.value = await api.fetchWorldGeo()
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function loadScenarioDoc(id: string) {
    const local = localDocs.get(id)
    if (local) {
      scenarioDoc.value = local
      return
    }
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
      await adoptRun(next, child, 'current')
      if (isMock)
        toast.push(`Mock mode: "${child.name}" re-used the parent's results (no engine).`, 'warn')
      else toast.push(`Ran ${child.name} (${next.meta.draws} draws).`)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  function registerScenario(id: string, s: ScenarioDocument) {
    localDocs.set(id, s)
    if (!scenarios.value.some((x) => x.id === id))
      scenarios.value = [
        ...scenarios.value,
        { id, name: s.name, parent: s.parent, description: s.description ?? '', user: true },
      ]
  }

  /**
   * Adopts a finished run as the current scenario (A) or as the compare scenario (B). B is keyed
   * by its result hash so `compare=` in the URL resolves through GET /api/results/{hash}
   * (contracts §10) even though the child scenario was never saved.
   */
  async function adoptRun(
    next: ResultsDocument,
    scenario: ScenarioDocument,
    as: 'current' | 'compare',
  ): Promise<ResultsDocument> {
    const hash = next.meta.scenario_hash
    localDocs.set(hash, scenario)
    if (as === 'current') {
      registerScenario(scenario.id, scenario)
      doc.value = next
      scenarioId.value = scenario.id
      scenarioDoc.value = scenario
      if (compareId.value === hash) setCompare(null)
      else if (compareId.value) void loadCompare()
      return next
    }
    registerScenario(hash, scenario)
    docB.value = next
    compareId.value = hash
    const a = doc.value
    if (a) {
      compareLoading.value = true
      try {
        compare.value = await api.compareRuns(a, next, regionStore.region)
      } catch (e) {
        error.value = (e as Error).message
      } finally {
        compareLoading.value = false
      }
    }
    return next
  }

  /** Runs a scenario document (a chat proposal, contracts §17) and adopts the result. */
  async function runProposal(scenario: ScenarioDocument, as: 'current' | 'compare') {
    error.value = null
    const busy = as === 'current' ? loading : compareLoading
    busy.value = true
    try {
      const next = await api.runScenarioDoc(scenario)
      await adoptRun(next, scenario, as)
      if (isMock)
        useToastStore().push(
          `Mock mode: "${scenario.name}" re-used the parent's results (no engine).`,
          'warn',
        )
      return next
    } catch (e) {
      error.value = (e as Error).message
      return null
    } finally {
      busy.value = false
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
      const have = docB.value
      const next =
        have && (have.meta.scenario_id === b || have.meta.scenario_hash === b)
          ? have
          : await api.runScenario(b)
      docB.value = next
      compare.value = await api.compareRuns(a, next, regionStore.region)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      compareLoading.value = false
    }
  }

  // the paired delta is per region: recompute when the selection changes
  watch(
    () => regionStore.region,
    () => {
      if (compareId.value && doc.value) void loadCompare()
    },
  )

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
    worldGeo,
    regions,
    world,
    supply,
    regionIds,
    hasRegion,
    seriesB,
    rents,
    regionInfo,
    isRegionFixture,
    loadWorldGeo,
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
    isStatic,
    national,
    confidenceAt,
    loadScenarios,
    loadLevers,
    loadGeo,
    loadScenarioDoc,
    runScenario,
    runChild,
    adoptRun,
    runProposal,
    saveScenario,
    loadCompare,
    setCompare,
  }
})
