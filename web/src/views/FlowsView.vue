<script setup lang="ts">
import { computed } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useRegionStore } from '@/stores/region'
import { useThemeStore } from '@/stores/theme'
import { fmtCompact, quarterLabel } from '@/lib/format'
import { stackCategorical } from '@/lib/scales'
import { FLOW_DESTINATION_LABELS } from '@/lib/metrics'
import { FLOW_DESTINATIONS } from '@/types/results'
import SankeyChart from '@/components/charts/SankeyChart.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const regionStore = useRegionStore()
const theme = useThemeStore()
/** Phase 3: the flow section is U.S.-only; the selected region's cumulative displacement is shown for context. */
const regionDisplaced = computed(() => {
  const s = results.series?.displaced_workers_cum
  return s ? fmtCompact(s.p50[scrubber.q]) : '—'
})

const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const total = computed(() =>
  results.flows ? results.flows.origins.reduce((a, o) => a + (o.jobs_lost_cum.p50[scrubber.q] ?? 0), 0) : 0,
)
const color = computed(() =>
  stackCategorical(results.flows?.origins.map((o) => o.major_group) ?? [], theme.mode),
)
const destRows = computed(() =>
  results.flows
    ? FLOW_DESTINATIONS.map((d) => {
        const s = results.flows!.destinations[d]
        return { d, label: FLOW_DESTINATION_LABELS[d], v: s.p50[scrubber.q] ?? 0, lo: s.p10?.[scrubber.q], hi: s.p90?.[scrubber.q] }
      })
    : [],
)
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>Where displaced U.S. workers went, 2024 → {{ qLabel }} (cumulative)</h2>
      <span
        v-if="regionStore.region !== 'US'"
        class="badge composition"
        :title="`Flows are published for the U.S. only in Phase 3; ${regionStore.label} cumulative displacement is ${regionDisplaced}`"
        >flows U.S.-only · {{ regionStore.label }} displaced {{ regionDisplaced }}</span
      >
      <span class="chart-note">
        Flow widths carry the median; hover for the 10–90 band. Total displaced:
        <strong class="mono">{{ fmtCompact(total) }}</strong>
      </span>
    </div>
    <div class="filters">
      <div class="legend" role="list" aria-label="Origin groups">
        <span v-for="o in results.flows?.origins ?? []" :key="o.major_group" class="item" role="listitem">
          <span class="sw" :style="{ background: color(o.major_group) }"></span>{{ o.title }}
        </span>
      </div>
    </div>
    <div v-if="results.flows" class="layout">
      <div class="card plot">
        <SankeyChart :flows="results.flows" :q="scrubber.q" :mode="theme.mode" :quarter-label="qLabel" />
      </div>
      <aside class="card side">
        <h3>Destinations, {{ qLabel }}</h3>
        <table class="data">
          <thead>
            <tr>
              <th>State</th>
              <th class="num">Median</th>
              <th class="num">10–90</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in destRows" :key="r.d">
              <td>{{ r.label }}</td>
              <td class="num">{{ fmtCompact(r.v) }}</td>
              <td class="num muted">
                {{ r.lo != null && r.hi != null ? `${fmtCompact(r.lo)}–${fmtCompact(r.hi)}` : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
        <p class="chart-note">
          The results document publishes origin and destination totals; origin → destination
          links are drawn as origin × destination share until the engine publishes the joint flow.
        </p>
      </aside>
    </div>
    <div v-else class="card empty">
      <p class="muted">This run has no flows section (Phase 2 results only).</p>
    </div>
  </section>
</template>

<style scoped>
.badge.composition {
  background: var(--surface-2);
  color: var(--ink-2);
}
.layout {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}
.plot {
  flex: 1;
  min-width: 0;
  min-height: 460px;
  padding: 8px;
  display: flex;
}
.side {
  width: 340px;
  flex-shrink: 0;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.side table.data th,
.side table.data td {
  white-space: normal;
  padding: 6px 6px;
}
.legend {
  display: inline-flex;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--ink-2);
}
.item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  display: inline-block;
}
.empty {
  padding: 28px;
}
</style>
