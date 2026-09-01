import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { StateMetric } from '@/types/results'
import { STATE_METRIC_KEYS } from '@/lib/metrics'

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
  let timer: ReturnType<typeof setInterval> | null = null

  const maxQ = computed(() => Math.max(0, length.value - 1))
  const atEnd = computed(() => q.value >= maxQ.value)

  function setLength(n: number) {
    length.value = n
    if (q.value > maxQ.value) q.value = maxQ.value
  }

  function set(i: number) {
    if (!Number.isFinite(i)) return
    q.value = Math.min(maxQ.value, Math.max(0, Math.round(i)))
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

  /** URL query fragment carried by the scrubber store. Omits defaults. */
  function toQuery(): UrlQuery {
    return {
      q: q.value > 0 ? String(q.value) : undefined,
      metric: metric.value !== 'employment_pct_vs_baseline' ? metric.value : undefined,
      state: state.value ?? undefined,
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
  }

  return {
    q,
    length,
    playing,
    metric,
    state,
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
    toQuery,
    applyQuery,
  }
})
