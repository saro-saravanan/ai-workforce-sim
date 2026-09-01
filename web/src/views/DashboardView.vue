<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useThemeStore } from '@/stores/theme'
import { DASHBOARD_TILES } from '@/lib/metrics'
import { CATEGORICAL } from '@/lib/palette'
import { quarterLabel } from '@/lib/format'
import type { NationalMetric } from '@/types/results'
import StatTile from '@/components/StatTile.vue'
import SeriesChart from '@/components/charts/SeriesChart.vue'
import StackedChannels from '@/components/charts/StackedChannels.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const theme = useThemeStore()

const expanded = ref<NationalMetric | null>(null)
const hue = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const tiles = computed(() =>
  DASHBOARD_TILES.map((t) => ({ ...t, series: results.national(t.key) })).filter((t) => t.series),
)
const expandedTile = computed(() => tiles.value.find((t) => t.key === expanded.value))
const expandedChannels = computed(() =>
  expanded.value ? results.channels[expanded.value] : undefined,
)
const hasAnyBand = computed(() => tiles.value.some((t) => t.series?.p10 && t.series?.p90))

function toggle(k: NationalMetric) {
  expanded.value = expanded.value === k ? null : k
}
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>US economy vs no-AI baseline, {{ qLabel }}</h2>
      <span class="chart-note">
        Median line{{ hasAnyBand ? ' with 10–90 band' : '' }}; dotted line = baseline (no frontier
        AI after 2023). Click a tile to expand.
      </span>
    </div>
    <div class="tiles">
      <StatTile
        v-for="t in tiles"
        :key="t.key"
        :label="t.def.label"
        :unit="t.def.unit"
        :series="t.series!"
        :q="scrubber.q"
        :hue="hue"
        :format="t.def.format"
        :zero="t.def.polarity === 'diverging'"
        :expanded="expanded === t.key"
        @toggle="toggle(t.key)"
      />
    </div>
    <div v-if="expandedTile && expandedTile.series" class="card expanded">
      <div class="exp-head">
        <h3>
          {{ expandedTile.def.label }} <span class="muted">({{ expandedTile.def.unit }})</span>
        </h3>
        <button class="btn" @click="expanded = null">Close</button>
      </div>
      <SeriesChart
        :series="expandedTile.series"
        :quarters="results.quarters"
        :q="scrubber.q"
        :hue="hue"
        :label="expandedTile.def.label"
        :format="(v) => expandedTile!.def.format(v)"
        :axis-format="expandedTile.def.axisFormat"
        :zero="expandedTile.def.polarity === 'diverging'"
        @scrub="scrubber.set($event)"
      />
      <template v-if="expandedChannels">
        <h3 class="sub">Channel decomposition</h3>
        <p class="chart-note">
          Stacked contributions sum to the net line; hover for values, click the chart to move the
          scrubber.
        </p>
        <StackedChannels
          :channels="expandedChannels"
          :net="expandedTile.series"
          :quarters="results.quarters"
          :q="scrubber.q"
          :mode="theme.mode"
          :format="(v) => expandedTile!.def.format(v)"
          :axis-format="expandedTile.def.axisFormat"
          :unit="expandedTile.def.unit"
        />
      </template>
      <p v-else class="chart-note">
        No channel decomposition is published for this metric in this run.
      </p>
    </div>
  </section>
</template>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
@media (min-width: 1100px) {
  .tiles {
    grid-template-columns: repeat(3, 1fr);
  }
}
.expanded {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.exp-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sub {
  margin-top: 10px;
}
</style>
