<script setup lang="ts">
import { computed } from 'vue'
import type { Series } from '@/types/results'
import type { FanChart } from '@/types/story'
import { useScrubberStore } from '@/stores/scrubber'
import { useThemeStore } from '@/stores/theme'
import { CATEGORICAL } from '@/lib/palette'
import { fmtPct } from '@/lib/format'
import { RANGE_TITLE } from '@/lib/story'
import SeriesChart from '@/components/charts/SeriesChart.vue'

/** The jobs beat: employment and GDP, p10–p90 band with the median line, over the quarters. */
const props = defineProps<{ chart: FanChart }>()
const scrubber = useScrubberStore()
const theme = useThemeStore()

const hue = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const hue2 = computed(() => CATEGORICAL[theme.mode][2] ?? '#1baf7a')
const toSeries = (s: FanChart['series']['employment']): Series => ({
  p50: s.p50 ?? [],
  p10: s.p10,
  p90: s.p90,
})
const panels = computed(() => [
  {
    key: 'employment',
    label: 'Jobs',
    series: toSeries(props.chart.series.employment),
    hue: hue.value,
  },
  { key: 'gdp', label: 'Economy (GDP)', series: toSeries(props.chart.series.gdp), hue: hue2.value },
])
const q = computed(() => Math.min(scrubber.q, Math.max(0, props.chart.quarters.length - 1)))
const axis = (v: number) => `${v > 0 ? '+' : ''}${v}%`
</script>

<template>
  <div class="fan">
    <p class="muted note" :title="RANGE_TITLE">
      % versus no AI · median line, range of the model's assumptions shaded
    </p>
    <div v-for="pn in panels" :key="pn.key" class="panel">
      <div class="head">
        <span class="sw" :style="{ background: pn.hue }"></span>
        <strong>{{ pn.label }}</strong>
      </div>
      <SeriesChart
        :series="pn.series"
        :quarters="chart.quarters"
        :q="q"
        :hue="pn.hue"
        :label="pn.label"
        :format="(v) => fmtPct(v)"
        :axis-format="axis"
        :height="200"
        zero
        @scrub="scrubber.set($event)"
      />
    </div>
  </div>
</template>

<style scoped>
.fan {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 4px 12px;
}
.note {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 14px;
}
.panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  flex-wrap: wrap;
}
.sw {
  width: 12px;
  height: 3px;
  border-radius: 2px;
  display: inline-block;
}
</style>
