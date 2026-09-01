import { watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { useScrubberStore } from '@/stores/scrubber'
import { useResultsStore } from '@/stores/results'

/** Two-way binding between the URL query (scenario, q, metric, state) and the stores. */
export function useUrlSync() {
  const route = useRoute()
  const router = useRouter()
  const scrubber = useScrubberStore()
  const results = useResultsStore()
  let applying = false

  const str = (v: unknown) =>
    typeof v === 'string' ? v : Array.isArray(v) ? String(v[0] ?? '') : undefined

  function fromRoute() {
    applying = true
    scrubber.applyQuery({
      q: str(route.query.q),
      metric: str(route.query.metric),
      state: str(route.query.state),
    })
    const sc = str(route.query.scenario)
    if (sc && sc !== results.scenarioId) results.scenarioId = sc
    applying = false
  }

  fromRoute()
  watch(() => route.query, fromRoute)

  watch(
    () => [scrubber.q, scrubber.metric, scrubber.state, results.scenarioId] as const,
    () => {
      if (applying) return
      const next: LocationQueryRaw = { ...route.query, ...scrubber.toQuery() }
      next.scenario = results.scenarioId !== 'baseline' ? results.scenarioId : undefined
      for (const k of Object.keys(next)) if (next[k] === undefined) delete next[k]
      router.replace({ query: next })
    },
  )
}
