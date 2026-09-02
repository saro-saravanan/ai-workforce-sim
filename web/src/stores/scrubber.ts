import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { CohortFacet, StateMetric } from '@/types/results'
import { STATE_METRIC_KEYS } from '@/lib/metrics'

/** URL value ↔ cohort facet key (`cohort=age|education|income`) */
export const COHORT_URL: Record<CohortFacet, string> = {
  age: 'age',
  education: 'education',
  income_decile: 'income',
}
const COHORT_FROM_URL: Record<string, CohortFacet> = {
  age: 'age',
  education: 'education',
  income: 'income_decile',
}

export const PLAYBACK_QPS = 4 // quarters per second
export const PLAYBACK_MS = 1000 / PLAYBACK_QPS

export type UrlQuery = Record<string, string | undefined>

/**
 * Global time scrubber + the URL-carried view state (q, metric, state).
 * The store is router-agnostic: `toQuery()` / `applyQuery()` are wired to vue-router by
 * `useUrlSync()` so the store stays unit-testable.
 */
export const useScrubberStore = defineStore('scrubber', () => {
  const q = ref(0)
  const length = ref(0)
  const playing = ref(false)
  const metric = ref<StateMetric>('employment_pct_vs_baseline')
  const state = ref<string | null>(null)
  /** Phase 2: cohort facet (`cohort=`) and structural mechanism cell (`cell=`) */
  const cohort = ref<CohortFacet>('age')
  const cell = ref<string | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null

  const maxQ = computed(() => Math.max(0, length.value - 1))
  const atEnd = computed(() => q.value >= maxQ.value)

  function setLength(n: number) {
    length.value = n
    if (q.value > maxQ.value) q.value = maxQ.value
  }

  function set(i: number) {
    if (!Number.isFinite(i)) return
    // before the results document is loaded (length 0) keep the requested quarter; setLength clamps it
    q.value = length.value > 0 ? Math.min(maxQ.value, Math.max(0, Math.round(i))) : Math.max(0, Math.round(i))
  }

  function step(delta: number) {
    set(q.value + delta)
  }

  function play() {
    if (playing.value) return
    if (atEnd.value) q.value = 0
    playing.value = true
    timer = setInterval(() => {
      if (q.value >= maxQ.value) {
        pause()
        return
      }
      q.value += 1
    }, PLAYBACK_MS)
  }

  function pause() {
    playing.value = false
    if (timer) clearInterval(timer)
    timer = null
  }

  function toggle() {
    if (playing.value) pause()
    else play()
  }

  function setMetric(m: string) {
    if ((STATE_METRIC_KEYS as string[]).includes(m)) metric.value = m as StateMetric
  }

  function selectState(fips: string | null) {
    state.value = fips
  }

  function setCohort(c: string) {
    if (c in COHORT_URL) cohort.value = c as CohortFacet
    else if (c in COHORT_FROM_URL) cohort.value = COHORT_FROM_URL[c]!
  }

  function selectCell(id: string | null) {
    cell.value = id
  }

  /** URL query fragment carried by the scrubber store. Omits defaults. */
  function toQuery(): UrlQuery {
    return {
      q: q.value > 0 ? String(q.value) : undefined,
      metric: metric.value !== 'employment_pct_vs_baseline' ? metric.value : undefined,
      state: state.value ?? undefined,
      cohort: cohort.value !== 'age' ? COHORT_URL[cohort.value] : undefined,
      cell: cell.value ?? undefined,
    }
  }

  /** Apply a URL query (strings) to the store. Unknown/invalid values are ignored. */
  function applyQuery(query: UrlQuery) {
    if (query.q != null) {
      const n = Number(query.q)
      if (Number.isFinite(n)) set(n)
    } else {
      q.value = 0
    }
    metric.value =
      query.metric && (STATE_METRIC_KEYS as string[]).includes(query.metric)
        ? (query.metric as StateMetric)
        : 'employment_pct_vs_baseline'
    state.value = query.state && /^\d{2}$/.test(query.state) ? query.state : null
    cohort.value = (query.cohort && COHORT_FROM_URL[query.cohort]) || 'age'
    cell.value = query.cell && /^[a-z0-9_|-]{1,80}$/.test(query.cell) ? query.cell : null
  }

  return {
    q,
    length,
    playing,
    metric,
    state,
    cohort,
    cell,
    maxQ,
    atEnd,
    setLength,
    set,
    step,
    play,
    pause,
    toggle,
    setMetric,
    selectState,
    setCohort,
    selectCell,
    toQuery,
    applyQuery,
  }
})
