<script setup lang="ts">
import { computed } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useThemeStore } from '@/stores/theme'
import { STATE_METRICS, STATE_METRIC_KEYS } from '@/lib/metrics'
import {
  divergingScale,
  magnitudeDomain,
  niceSymmetric,
  sequentialScale,
  symmetricDomain,
} from '@/lib/scales'
import { quarterLabel } from '@/lib/format'
import type { StateMetric, StateResult } from '@/types/results'
import ChoroplethMap, { type StateValue } from '@/components/charts/ChoroplethMap.vue'
import ColorLegend from '@/components/charts/ColorLegend.vue'
import SparkLine from '@/components/charts/SparkLine.vue'
import { CATEGORICAL } from '@/lib/palette'

const results = useResultsStore()
const scrubber = useScrubberStore()
const theme = useThemeStore()
results.loadGeo()

const metric = computed(() => scrubber.metric)
const def = computed(() => STATE_METRICS[metric.value])
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))

/** Domain over ALL quarters so the legend is stable while scrubbing. */
const domain = computed<[number, number]>(() => {
  const all: number[] = []
  for (const s of results.states) for (const v of s[metric.value].p50) all.push(v)
  return def.value.polarity === 'diverging'
    ? niceSymmetric(symmetricDomain(all))
    : magnitudeDomain(all)
})
const color = computed(() =>
  def.value.polarity === 'diverging'
    ? divergingScale(domain.value, theme.mode)
    : sequentialScale(domain.value, theme.mode, 'red'),
)

const values = computed(() => {
  const m = new Map<string, StateValue>()
  for (const s of results.states) {
    const ser = s[metric.value]
    m.set(s.fips, {
      value: ser.p50[scrubber.q],
      lo: ser.p10?.[scrubber.q],
      hi: ser.p90?.[scrubber.q],
    })
  }
  return m
})

const byFips = computed(() => new Map(results.states.map((s) => [s.fips, s])))
function extraRows(fips: string) {
  const s = byFips.value.get(fips)
  if (!s) return []
  return STATE_METRIC_KEYS.filter((k) => k !== metric.value).map((k) => ({
    label: STATE_METRICS[k].short,
    value: STATE_METRICS[k].format(s[k].p50[scrubber.q]),
  }))
}

const selected = computed<StateResult | undefined>(() =>
  scrubber.state ? byFips.value.get(scrubber.state) : undefined,
)
const national = computed(() => {
  const ser = results.series?.[metric.value]
  return ser ? def.value.format(ser.p50[scrubber.q]) : '—'
})
const hue = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')

function setMetric(k: StateMetric) {
  scrubber.setMetric(k)
}
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>{{ def.label }}{{ def.polarity === 'diverging' ? ' vs baseline' : '' }}, {{ qLabel }}</h2>
      <nav class="crumbs" aria-label="Breadcrumb">
        <button class="crumb" :class="{ current: !selected }" @click="scrubber.selectState(null)">
          United States
        </button>
        <template v-if="selected">
          <span class="muted">›</span>
          <span class="crumb current">{{ selected.name }}</span>
        </template>
      </nav>
      <span
        v-if="results.isFixture"
        class="badge fixture"
        title="occ_state is a fixture: same occupational mix in every state"
        >fixture data</span
      >
    </div>
    <div class="filters">
      <span class="muted">Metric</span>
      <div class="seg" role="group" aria-label="Metric">
        <button
          v-for="k in STATE_METRIC_KEYS"
          :key="k"
          class="btn"
          :aria-pressed="metric === k"
          @click="setMetric(k)"
        >
          {{ STATE_METRICS[k].short }}
        </button>
      </div>
      <span class="muted"
        >US total: <strong class="mono">{{ national }}</strong></span
      >
    </div>
    <div class="map-layout">
      <div class="card map-card">
        <ChoroplethMap
          v-if="results.geo"
          :geo="results.geo"
          :values="values"
          :color="color"
          :format="def.format"
          :metric-label="def.label"
          :selected="scrubber.state"
          :extra="extraRows"
          @select="scrubber.selectState($event)"
        />
        <p v-else class="muted loading">Loading state geometry…</p>
        <div class="legend-row">
          <ColorLegend
            :color="color"
            :domain="domain"
            :format="def.axisFormat"
            :title="`${def.label} · ${def.unit}`"
            :diverging="def.polarity === 'diverging'"
          />
          <span class="chart-note"
            >Hover for values; click a state to select it. Scale spans all quarters.</span
          >
        </div>
      </div>
      <aside v-if="selected" class="card detail">
        <h3>{{ selected.name }}</h3>
        <p class="muted small">Selected state · {{ qLabel }}</p>
        <div v-for="k in STATE_METRIC_KEYS" :key="k" class="detail-row">
          <div class="detail-head">
            <span class="muted">{{ STATE_METRICS[k].label }}</span>
            <strong class="mono">{{ STATE_METRICS[k].format(selected[k].p50[scrubber.q]) }}</strong>
          </div>
          <SparkLine
            :series="selected[k]"
            :q="scrubber.q"
            :hue="hue"
            :zero="STATE_METRICS[k].polarity === 'diverging'"
          />
        </div>
        <button class="btn" @click="scrubber.selectState(null)">Clear selection</button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.crumbs {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}
.crumb {
  border: 0;
  background: transparent;
  color: var(--accent-ink);
  cursor: pointer;
  padding: 0;
  font-size: 14px;
}
.crumb.current {
  color: var(--ink);
  font-weight: 600;
  cursor: default;
}
.map-layout {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}
.map-card {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 8px;
}
.map-card > :first-child {
  flex: 1;
  min-height: 380px;
}
.legend-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 6px 8px 4px;
}
.detail {
  width: 280px;
  flex-shrink: 0;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.detail .small {
  font-size: 14px;
  margin: 0;
}
.detail-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}
.loading {
  padding: 40px;
  text-align: center;
}
</style>
