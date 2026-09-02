<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useThemeStore } from '@/stores/theme'
import { DASHBOARD_TILES } from '@/lib/metrics'
import { CATEGORICAL } from '@/lib/palette'
import { quarterLabel } from '@/lib/format'
import { referenceQuarter } from '@/lib/confidence'
import type { HeadlineMetric, NationalMetric } from '@/types/results'
import { HEADLINE_METRICS } from '@/types/results'
import StatTile from '@/components/StatTile.vue'
import ConfidenceGlyph from '@/components/ConfidenceGlyph.vue'
import SeriesChart, { type Overlay } from '@/components/charts/SeriesChart.vue'
import StackedChannels from '@/components/charts/StackedChannels.vue'
import TornadoChart from '@/components/charts/TornadoChart.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const theme = useThemeStore()

const expanded = ref<NationalMetric | null>(null)
const ensembleView = ref<'parametric' | 'structural'>('parametric')
const hue = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const cellHue = computed(() => CATEGORICAL[theme.mode][1] ?? '#eb6834')
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const refQ = computed(() => referenceQuarter(results.quarters, scrubber.q))
const tiles = computed(() =>
  DASHBOARD_TILES.map((t) => ({ ...t, series: results.national(t.key) })).filter((t) => t.series),
)
const expandedTile = computed(() => tiles.value.find((t) => t.key === expanded.value))
const expandedChannels = computed(() =>
  expanded.value ? results.channels[expanded.value] : undefined,
)
const hasAnyBand = computed(() => tiles.value.some((t) => t.series?.p10 && t.series?.p90))
const hasInner = computed(() => tiles.value.some((t) => t.series?.p25 && t.series?.p75))

function isHeadline(k: NationalMetric | null): k is HeadlineMetric {
  return !!k && (HEADLINE_METRICS as string[]).includes(k)
}
const expandedStructural = computed(() =>
  isHeadline(expanded.value) ? results.structural[expanded.value] : undefined,
)
const expandedTornado = computed(() =>
  isHeadline(expanded.value) ? results.tornado[expanded.value] : undefined,
)
const expandedConfidence = computed(() =>
  isHeadline(expanded.value) ? results.confidenceAt(expanded.value, refQ.value) : undefined,
)
/** Cell ids split into their three axis parts for the legend. */
const cellList = computed(() =>
  Object.keys(expandedStructural.value?.by_cell ?? {}).map((id) => ({
    id,
    parts: id.split('|').map((p) => p.replace(/_/g, ' ')),
  })),
)
const overlays = computed<Overlay[]>(() => {
  const st = expandedStructural.value
  if (!st || ensembleView.value !== 'structural') return []
  return Object.entries(st.by_cell).map(([id, c]) => ({
    id,
    label: id.replace(/\|/g, ' · ').replace(/_/g, ' '),
    values: c.p50,
    emphasized: scrubber.cell === id,
    color: cellHue.value,
  }))
})
const spreadRows = computed(() => {
  const st = expandedStructural.value
  if (!st) return []
  return Object.entries(st.spread).map(([qk, s]) => ({ qk, ...s }))
})
const q2040 = computed(() => results.quarters.indexOf('2040Q4'))
const tornadoBase = computed(() => {
  const s = expandedTile.value?.series
  const i = q2040.value >= 0 ? q2040.value : results.quarters.length - 1
  return s ? (s.central?.[i] ?? s.p50[i] ?? 0) : 0
})

function toggle(k: NationalMetric) {
  expanded.value = expanded.value === k ? null : k
}
function selectCell(id: string) {
  scrubber.selectCell(scrubber.cell === id ? null : id)
}
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>US economy vs no-AI baseline, {{ qLabel }}</h2>
      <span class="chart-note">
        Median line{{ hasAnyBand ? ' with 10–90 band' : '' }}{{ hasInner ? ' (darker 25–75)' : '' }};
        dashed line = central-parameter run; dotted line = baseline (no frontier AI after 2023).
        Glyph = confidence at {{ quarterLabel(refQ) }} (● high ◐ medium ○ low). Click a tile to
        expand.
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
        :confidence="isHeadline(t.key) ? results.confidenceAt(t.key, refQ) : undefined"
        :confidence-at="isHeadline(t.key) ? refQ : undefined"
        @toggle="toggle(t.key)"
      />
    </div>
    <div v-if="expandedTile && expandedTile.series" class="card expanded">
      <div class="exp-head">
        <h3>
          {{ expandedTile.def.label }} <span class="muted">({{ expandedTile.def.unit }})</span>
          <ConfidenceGlyph
            v-if="expandedConfidence"
            :confidence="expandedConfidence"
            :at="refQ"
            with-label
            class="conf"
          />
        </h3>
        <div class="exp-tools">
          <div v-if="expandedStructural" class="seg" role="group" aria-label="Ensemble view">
            <button
              class="btn"
              :aria-pressed="ensembleView === 'parametric'"
              @click="ensembleView = 'parametric'"
            >
              Parametric
            </button>
            <button
              class="btn"
              :aria-pressed="ensembleView === 'structural'"
              @click="ensembleView = 'structural'"
            >
              Structural
            </button>
          </div>
          <button class="btn" @click="expanded = null">Close</button>
        </div>
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
        :overlays="overlays"
        @scrub="scrubber.set($event)"
      />
      <template v-if="expandedStructural && ensembleView === 'structural'">
        <div class="cells">
          <span class="chart-note">
            Thin lines = the eight mechanism-cell medians (demand response | reinstatement |
            pass-through). Click one to highlight it (<code>cell=</code> in the URL).
          </span>
          <div class="cell-list" role="list">
            <button
              v-for="c in cellList"
              :key="c.id"
              class="btn cell"
              role="listitem"
              :aria-pressed="scrubber.cell === c.id"
              @click="selectCell(c.id)"
            >
              <span class="sw" :style="{ background: scrubber.cell === c.id ? cellHue : 'var(--muted)' }"></span>
              <span v-for="(p, i) in c.parts" :key="i" class="part">{{ p }}</span>
            </button>
          </div>
        </div>
        <dl class="spread">
          <template v-for="r in spreadRows" :key="r.qk">
            <dt>{{ quarterLabel(r.qk) }}</dt>
            <dd>
              parametric <strong class="mono">{{ r.parametric_pp.toFixed(2) }} pp</strong>
              <span class="muted">(mean within-cell p90 − p10)</span> · structural
              <strong class="mono">{{ r.structural_pp.toFixed(2) }} pp</strong>
              <span class="muted">(range of cell medians)</span>
            </dd>
          </template>
        </dl>
      </template>
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
      <template v-if="expandedTornado && expandedTornado.length">
        <h3 class="sub">Sensitivity (tornado), 2040 Q4</h3>
        <p class="chart-note">
          Each parameter is moved to the low and high end of its range with everything else at
          central; bars show the resulting {{ expandedTile.def.label.toLowerCase() }}, sorted by
          swing.
        </p>
        <TornadoChart
          :rows="expandedTornado"
          :base="tornadoBase"
          :format="(v) => expandedTile!.def.format(v)"
          :axis-format="expandedTile.def.axisFormat"
          :mode="theme.mode"
          :unit="expandedTile.def.unit"
        />
      </template>
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
  gap: 12px;
  flex-wrap: wrap;
}
.exp-head h3 {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.exp-tools {
  display: flex;
  gap: 8px;
  align-items: center;
}
.sub {
  margin-top: 10px;
}
.cells {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cell-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.btn.cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 13px;
}
.btn.cell[aria-pressed='true'] {
  background: var(--surface-2);
  color: var(--ink);
  border-color: var(--ink-2);
}
.sw {
  width: 14px;
  height: 2px;
  display: inline-block;
}
.part + .part::before {
  content: '·';
  color: var(--muted);
  margin: 0 6px 0 0;
}
.spread {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  font-size: 14px;
}
.spread dt {
  font-weight: 600;
}
.spread dd {
  margin: 0;
}
</style>
