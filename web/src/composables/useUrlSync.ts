import { watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { useScrubberStore } from '@/stores/scrubber'
import { useResultsStore } from '@/stores/results'

/** Two-way binding between the URL query (scenario, q, metric, state, compare, cohort, cell) and the stores. */
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
      cohort: str(route.query.cohort),
      cell: str(route.query.cell),
    })
    const sc = str(route.query.scenario)
    if (sc && sc !== results.scenarioId) results.scenarioId = sc
    const cmp = str(route.query.compare)
    if ((cmp || null) !== results.compareId) results.setCompare(cmp || null)
    applying = false
  }

  fromRoute()
  watch(() => route.query, fromRoute)

  watch(
    () =>
      [
        scrubber.q,
        scrubber.metric,
        scrubber.state,
        scrubber.cohort,
        scrubber.cell,
        results.scenarioId,
        results.compareId,
      ] as const,
    () => {
      if (applying) return
      const next: LocationQueryRaw = { ...route.query, ...scrubber.toQuery() }
      next.scenario = results.scenarioId !== 'baseline' ? results.scenarioId : undefined
      next.compare = results.compareId ?? undefined
      for (const k of Object.keys(next)) if (next[k] === undefined) delete next[k]
      router.replace({ query: next })
    },
  )
}
