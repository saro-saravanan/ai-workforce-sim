<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useRegionStore } from '@/stores/region'
import { useThemeStore } from '@/stores/theme'
import { CATEGORICAL } from '@/lib/palette'
import { quarterLabel } from '@/lib/format'
import { COHORT_FACET_LABELS, COHORT_METRICS, cohortBandLabel, type CohortMetric } from '@/lib/metrics'
import { fmtPct } from '@/lib/format'
import type { CohortFacet } from '@/types/results'
import CohortBars from '@/components/charts/CohortBars.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const regionStore = useRegionStore()
const theme = useThemeStore()
/** Phase 3: the cohort split is U.S.-only; the selected region's headline is shown for context. */
const regionHeadline = computed(() => {
  const s = results.series?.employment_pct_vs_baseline
  return s ? fmtPct(s.p50[scrubber.q]) : '—'
})

const FACETS: CohortFacet[] = ['age', 'education', 'income_decile']
const metric = ref<CohortMetric>('employment_pct_vs_baseline')
const def = computed(() => COHORT_METRICS[metric.value])
const hue = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const selected = ref<{ facet: CohortFacet; band: string } | null>(null)

/** One x-domain across all three panels and all quarters, so bars are comparable and stable. */
const domain = computed<[number, number]>(() => {
  const c = results.cohorts
  if (!c) return [0, 1]
  let lo = 0
  let hi = 0
  for (const f of FACETS)
    for (const r of c[f]) {
      const s = r[metric.value]
      for (const arr of [s.p50, s.p10 ?? [], s.p90 ?? []])
        for (const v of arr) {
          lo = Math.min(lo, v)
          hi = Math.max(hi, v)
        }
    }
  if (lo === hi) hi = lo + 1
  return def.value.polarity === 'magnitude' ? [0, hi] : [lo, hi]
})

function select(facet: CohortFacet, band: string | null) {
  selected.value = band ? { facet, band } : null
}
const selectedLabel = computed(() =>
  selected.value ? `${COHORT_FACET_LABELS[selected.value.facet]} ${cohortBandLabel(selected.value.facet, selected.value.band)}` : '',
)
const selectedRow = computed(() => {
  if (!selected.value || !results.cohorts) return null
  const r = results.cohorts[selected.value.facet].find((x) => x.band === selected.value!.band)
  if (!r) return null
  const s = r[metric.value]
  return { v: s.p50[scrubber.q], lo: s.p10?.[scrubber.q], hi: s.p90?.[scrubber.q] }
})
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>Outcomes by cohort, US, {{ qLabel }}</h2>
      <span
        v-if="regionStore.region !== 'US'"
        class="badge composition"
        :title="`Cohort splits are published for the U.S. only in Phase 3; ${regionStore.label} net employment at ${qLabel} is ${regionHeadline}`"
        >cohorts U.S.-only · {{ regionStore.label }} net employment {{ regionHeadline }}</span
      >
      <span class="chart-note">
        Bars = median; whiskers = 10–90 band. One scale across the three panels.
      </span>
      <span
        v-if="results.meta?.data_flags.cohorts === 'FIXTURE'"
        class="badge fixture"
        title="cohort weights are the product of marginals until the CPS ASEC ingest"
        >fixture cohorts</span
      >
    </div>
    <div class="filters">
      <span class="muted">Metric</span>
      <div class="seg" role="group" aria-label="Cohort metric">
        <button
          v-for="(d, k) in COHORT_METRICS"
          :key="k"
          class="btn"
          :aria-pressed="metric === k"
          @click="metric = k as CohortMetric"
        >
          {{ d.label }}
        </button>
      </div>
      <span class="muted">Facet in URL</span>
      <div class="seg" role="group" aria-label="Primary facet">
        <button
          v-for="f in FACETS"
          :key="f"
          class="btn"
          :aria-pressed="scrubber.cohort === f"
          @click="scrubber.setCohort(f)"
        >
          {{ COHORT_FACET_LABELS[f] }}
        </button>
      </div>
      <span v-if="selected" class="muted">
        Selected: <strong>{{ selectedLabel }}</strong>
        <template v-if="selectedRow">
          · <span class="mono">{{ def.format(selectedRow.v) }}</span>
          <span v-if="selectedRow.lo != null" class="mono"
            >[{{ def.format(selectedRow.lo) }}, {{ def.format(selectedRow.hi) }}]</span
          >
        </template>
        <button class="btn tiny" @click="selected = null">clear</button>
      </span>
    </div>
    <div v-if="results.cohorts" class="panels">
      <div
        v-for="f in FACETS"
        :key="f"
        class="card panel"
        :class="{ primary: scrubber.cohort === f }"
      >
        <h3>{{ COHORT_FACET_LABELS[f] }}</h3>
        <CohortBars
          :rows="results.cohorts[f]"
          :metric="metric"
          :q="scrubber.q"
          :label="(b) => cohortBandLabel(f, b)"
          :domain="domain"
          :format="(v) => def.format(v)"
          :axis-format="def.axisFormat"
          :hue="hue"
          :zero="def.polarity === 'diverging'"
          :selected="selected?.facet === f ? selected.band : null"
          :title="COHORT_FACET_LABELS[f]"
          @select="select(f, $event)"
        />
      </div>
    </div>
    <div v-else class="card empty">
      <p class="muted">This run has no cohort section (Phase 2 results only).</p>
    </div>
    <p class="chart-note">
      {{ def.unit }}. Cohort weights are per-occupation marginals (age × education × decile,
      independent within occupation) until the CPS ASEC ingest fits the joint distribution.
    </p>
  </section>
</template>

<style scoped>
.badge.composition {
  background: var(--surface-2);
  color: var(--ink-2);
}
.panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
  align-items: start;
}
.panel {
  padding: 10px 12px 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.panel.primary {
  border-color: var(--ink-2);
}
.panel h3 {
  font-size: 14px;
  color: var(--ink-2);
}
.btn.tiny {
  padding: 2px 8px;
  margin-left: 6px;
}
.empty {
  padding: 28px;
}
</style>
