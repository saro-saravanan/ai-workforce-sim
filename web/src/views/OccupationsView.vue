<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useRegionStore } from '@/stores/region'
import { useThemeStore } from '@/stores/theme'
import { cappedCategorical } from '@/lib/scales'
import { quarterLabel } from '@/lib/format'
import { MAJOR_GROUPS } from '@/lib/metrics'
import { CATEGORICAL } from '@/lib/palette'
import type { OccupationResult } from '@/types/results'
import OccupationScatter, { type ScatterPoint } from '@/components/charts/OccupationScatter.vue'
import OccupationTable from '@/components/OccupationTable.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const regionStore = useRegionStore()
const theme = useThemeStore()

/**
 * Phase 3: non-U.S. regions carry a central-only path per occupation (`by_region`); the bands and
 * the wage columns stay U.S.-only. World shows the U.S. detail (there is no world occupation split).
 */
const regionKey = computed(() => regionStore.seriesKey)
const usesByRegion = computed(
  () =>
    !!regionKey.value &&
    regionKey.value !== 'US' &&
    results.occupations.some((o) => o.by_region?.[regionKey.value!]),
)
const regionNote = computed(() => {
  if (regionStore.isWorld) return 'Occupation detail is U.S.-only for World (no world occupation split).'
  if (regionKey.value === 'US') return ''
  if (usesByRegion.value)
    return `${regionStore.label}: central run only — bands and wage columns are U.S.-only in Phase 3.`
  return `No occupation paths for ${regionStore.label} in this run — showing the U.S.`
})
function displacementAt(occ: OccupationResult, q: number): number {
  if (usesByRegion.value) {
    const c = occ.by_region?.[regionKey.value!]?.displacement.central[q]
    if (c != null) return c
  }
  return occ.displacement.p50[q] ?? 0
}
/**
 * Phase 6: displacement through the embodied channels (`displacement_embodied`, central run,
 * U.S. only — contracts §20 publishes no regional split) and its ever-automatable mass.
 */
const hasEmbodied = computed(() => results.occupations.some((o) => o.displacement_embodied))
const channel = ref<'total' | 'embodied'>('total')
const showEmbodied = computed(() => hasEmbodied.value && channel.value === 'embodied')
function embodiedAt(occ: OccupationResult, q: number): number | undefined {
  return occ.displacement_embodied?.central[q]
}

const mode = ref<'scatter' | 'table'>('scatter')
const colorBy = ref<'group' | 'single'>('group')
const sortKey = ref<'gap' | 'y' | 'x' | 'emp0' | 'yEmb'>('gap')
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))

const points = computed<ScatterPoint[]>(() =>
  results.occupations.map((occ) => {
    const yEmb = hasEmbodied.value ? (embodiedAt(occ, scrubber.q) ?? 0) : undefined
    const x = showEmbodied.value ? (occ.automatable_share_embodied ?? 0) : occ.automatable_share
    const y = showEmbodied.value ? (yEmb ?? 0) : displacementAt(occ, scrubber.q)
    return { occ, x, y, gap: x - y, yEmb }
  }),
)
const yMax = computed(() => {
  let m = 0
  for (const o of results.occupations)
    for (let i = 0; i < o.displacement.p50.length; i++)
      m = Math.max(m, showEmbodied.value ? (embodiedAt(o, i) ?? 0) : displacementAt(o, i))
  return Math.max(0.1, Math.ceil((m + 0.02) * 10) / 10)
})

/** Top-3 major groups by 2023 employment get a hue; the rest fold to gray. */
const groupsByEmp = computed(() => {
  const tot = new Map<string, number>()
  for (const o of results.occupations)
    tot.set(o.major_group, (tot.get(o.major_group) ?? 0) + o.emp0)
  return [...tot.entries()].sort((a, b) => b[1] - a[1]).map(([g]) => g)
})
const cat = computed(() => cappedCategorical(groupsByEmp.value, theme.mode))
const single = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const color = computed(() =>
  colorBy.value === 'group'
    ? (o: OccupationResult) => cat.value.scale(o.major_group)
    : () => single.value,
)
const legend = computed(() =>
  cat.value.kept
    .map((g) => ({ key: g, label: MAJOR_GROUPS[g] ?? g, color: cat.value.scale(g) }))
    .concat([{ key: 'other', label: 'Other groups', color: cat.value.other }]),
)

const sorted = computed(() => {
  const k = sortKey.value
  const of = (p: ScatterPoint) => (k === 'emp0' ? p.occ.emp0 : k === 'yEmb' ? (p.yEmb ?? 0) : p[k])
  return [...points.value].sort((a, b) => of(b) - of(a))
})
const rankValue = (p: ScatterPoint) => {
  const k = sortKey.value
  if (k === 'emp0') return (p.occ.emp0 / 1e6).toFixed(1) + 'M'
  const v = k === 'yEmb' ? (p.yEmb ?? 0) : p[k]
  return (v * 100).toFixed(1) + '%'
}
/** Direct-label the headline: the five largest exposed-but-not-yet-hit occupations. */
const labelled = computed(() => {
  const ranked = [...points.value].sort((a, b) => b.gap * b.occ.emp0 - a.gap * a.occ.emp0)
  return new Set(ranked.slice(0, 8).map((p) => p.occ.occ_code))
})
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>
        Exposure vs realized displacement,
        {{ usesByRegion ? regionStore.label : 'US' }}, {{ qLabel }}
      </h2>
      <span class="chart-note"
        >Size = 2023 U.S. employment. Below the diagonal = exposed but not yet hit.<template
          v-if="showEmbodied"
        >
          Embodied channel only: x = ever-automatable mass on the embodiment classes, y = displacement
          through them (central run, U.S.).</template
        ></span
      >
      <span v-if="regionNote" class="badge composition" :title="regionNote">{{
        usesByRegion ? 'bands U.S.-only' : 'U.S. detail'
      }}</span>
    </div>
    <div class="filters">
      <div class="seg" role="group" aria-label="Rendering">
        <button class="btn" :aria-pressed="mode === 'scatter'" @click="mode = 'scatter'">
          Scatter
        </button>
        <button class="btn" :aria-pressed="mode === 'table'" @click="mode = 'table'">Table</button>
      </div>
      <template v-if="hasEmbodied">
        <span class="muted">Channel</span>
        <div class="seg" role="group" aria-label="Displacement channel">
          <button class="btn" :aria-pressed="channel === 'total'" @click="channel = 'total'">All</button>
          <button
            class="btn"
            :aria-pressed="channel === 'embodied'"
            title="Displacement through the embodied channels only (robotaxis, trucking, warehouse and fixed robots)"
            @click="channel = 'embodied'"
          >
            Embodied
          </button>
        </div>
      </template>
      <label class="muted"
        >Sort
        <select v-model="sortKey" class="select">
          <option value="gap">by gap (exposed − hit)</option>
          <option value="y">by displacement</option>
          <option v-if="hasEmbodied" value="yEmb">by embodied displacement</option>
          <option value="x">by automatable share</option>
          <option value="emp0">by employment</option>
        </select>
      </label>
      <template v-if="mode === 'scatter'">
        <span class="muted">Color</span>
        <div class="seg" role="group" aria-label="Color">
          <button class="btn" :aria-pressed="colorBy === 'group'" @click="colorBy = 'group'">
            Major group
          </button>
          <button class="btn" :aria-pressed="colorBy === 'single'" @click="colorBy = 'single'">
            Single hue
          </button>
        </div>
        <div v-if="colorBy === 'group'" class="legend" role="list" aria-label="Major group colors">
          <span v-for="l in legend" :key="l.key" class="item" role="listitem">
            <span class="sw" :style="{ background: l.color }"></span>{{ l.label }}
          </span>
        </div>
      </template>
    </div>
    <div class="body">
      <div v-if="mode === 'scatter'" class="card plot">
        <OccupationScatter
          :points="sorted"
          :y-max="yMax"
          :color="color"
          :quarter-label="qLabel"
          :labelled="labelled"
        />
      </div>
      <OccupationTable v-else :points="points" :q="scrubber.q" :quarter-label="qLabel" />
    </div>
    <p v-if="regionNote" class="chart-note">{{ regionNote }}</p>
    <ol class="rank" aria-label="Largest gaps">
      <li v-for="p in sorted.slice(0, 5)" :key="p.occ.occ_code">
        <span>{{ p.occ.title }}</span>
        <strong class="mono">{{ rankValue(p) }}</strong>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.badge.composition {
  background: var(--surface-2);
  color: var(--ink-2);
}
.body {
  flex: 1;
  min-height: 0;
  display: flex;
}
.plot {
  flex: 1;
  min-width: 0;
  padding: 8px;
  min-height: 420px;
  display: flex;
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
  border-radius: 50%;
  display: inline-block;
}
.rank {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 14px;
  color: var(--ink-2);
}
.rank li {
  display: inline-flex;
  gap: 8px;
}
.rank strong {
  color: var(--ink);
}
</style>
