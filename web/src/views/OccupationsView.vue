<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
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
const theme = useThemeStore()

const mode = ref<'scatter' | 'table'>('scatter')
const colorBy = ref<'group' | 'single'>('group')
const sortKey = ref<'gap' | 'y' | 'x' | 'emp0'>('gap')
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))

const points = computed<ScatterPoint[]>(() =>
  results.occupations.map((occ) => {
    const x = occ.automatable_share
    const y = occ.displacement.p50[scrubber.q] ?? 0
    return { occ, x, y, gap: x - y }
  }),
)
const yMax = computed(() => {
  let m = 0
  for (const o of results.occupations) for (const v of o.displacement.p50) m = Math.max(m, v)
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
  return [...points.value].sort((a, b) => {
    const va = k === 'emp0' ? a.occ.emp0 : a[k]
    const vb = k === 'emp0' ? b.occ.emp0 : b[k]
    return vb - va
  })
})
/** Direct-label the headline: the five largest exposed-but-not-yet-hit occupations. */
const labelled = computed(() => {
  const ranked = [...points.value].sort((a, b) => b.gap * b.occ.emp0 - a.gap * a.occ.emp0)
  return new Set(ranked.slice(0, 8).map((p) => p.occ.occ_code))
})
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>Exposure vs realized displacement, {{ qLabel }}</h2>
      <span class="chart-note"
        >Size = 2023 employment. Below the diagonal = exposed but not yet hit.</span
      >
    </div>
    <div class="filters">
      <div class="seg" role="group" aria-label="Rendering">
        <button class="btn" :aria-pressed="mode === 'scatter'" @click="mode = 'scatter'">
          Scatter
        </button>
        <button class="btn" :aria-pressed="mode === 'table'" @click="mode = 'table'">Table</button>
      </div>
      <label class="muted"
        >Sort
        <select v-model="sortKey" class="select">
          <option value="gap">by gap (exposed − hit)</option>
          <option value="y">by displacement</option>
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
    <ol class="rank" aria-label="Largest gaps">
      <li v-for="p in sorted.slice(0, 5)" :key="p.occ.occ_code">
        <span>{{ p.occ.title }}</span>
        <strong class="mono">{{
          sortKey === 'emp0'
            ? (p.occ.emp0 / 1e6).toFixed(1) + 'M'
            : (p[sortKey] * 100).toFixed(1) + '%'
        }}</strong>
      </li>
    </ol>
  </section>
</template>

<style scoped>
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
