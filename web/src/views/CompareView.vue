<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { extent } from 'd3'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useThemeStore } from '@/stores/theme'
import { CATEGORICAL } from '@/lib/palette'
import { divergingScale, niceSymmetric, symmetricDomain } from '@/lib/scales'
import { fmtPct, fmtShare, quarterLabel } from '@/lib/format'
import { COMPARE_METRICS, HEADLINE_LABELS, TRACE_LABELS, metricDef } from '@/lib/metrics'
import { fmtLeverValue } from '@/lib/levers'
import { referenceQuarter } from '@/lib/confidence'
import { seriesExtentValues } from '@/lib/bands'
import type { HeadlineMetric, NationalMetric, Series, TraceKey } from '@/types/results'
import { HEADLINE_METRICS } from '@/types/results'
import SeriesChart from '@/components/charts/SeriesChart.vue'
import ChoroplethMap, { type StateValue } from '@/components/charts/ChoroplethMap.vue'
import ColorLegend from '@/components/charts/ColorLegend.vue'
import DeltaBars, { type DeltaRow } from '@/components/charts/DeltaBars.vue'
import ConfidenceGlyph from '@/components/ConfidenceGlyph.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const theme = useThemeStore()
results.loadGeo()

const metric = ref<NationalMetric>('employment_pct_vs_baseline')
const def = computed(() => metricDef(metric.value))
const hueA = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const hueB = computed(() => CATEGORICAL[theme.mode][1] ?? '#eb6834')
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const refQ = computed(() => referenceQuarter(results.quarters, scrubber.q))

const groups = computed(() => [
  { label: 'Scenarios', items: results.scenarios.filter((s) => !s.preset && !s.user) },
  { label: 'Report presets', items: results.scenarios.filter((s) => s.preset) },
  { label: 'Saved', items: results.scenarios.filter((s) => s.user) },
])
/** Default B: the first scenario that is not A. */
watch(
  () => [results.scenarios.length, results.compareId] as const,
  () => {
    if (!results.compareId && results.scenarios.length) {
      const other = results.scenarios.find((s) => s.id !== results.scenarioId)
      if (other) results.setCompare(other.id)
    }
  },
  { immediate: true },
)
function onPickB(e: Event) {
  results.setCompare((e.target as HTMLSelectElement).value || null)
}
function swap() {
  const b = results.compareId
  if (!b) return
  const a = results.scenarioId
  results.scenarioId = b
  results.setCompare(a)
}

const seriesA = computed(() => results.series?.[metric.value])
const seriesB = computed(() => results.docB?.series.US?.[metric.value])
/** shared y domain so both panels read on one scale */
const yDomain = computed<[number, number]>(() => {
  const all: number[] = []
  if (seriesA.value) all.push(...seriesExtentValues(seriesA.value))
  if (seriesB.value) all.push(...seriesExtentValues(seriesB.value))
  if (def.value.polarity === 'diverging') all.push(0)
  const [lo, hi] = extent(all) as [number, number]
  const padv = ((hi ?? 0) - (lo ?? 0) || 1) * 0.08
  return [(lo ?? 0) - padv, (hi ?? 0) + padv]
})
const delta = computed<Series | undefined>(() => {
  const d = results.compare?.delta.series[metric.value]
  return d ? { p10: d.p10, p50: d.p50, p90: d.p90 } : undefined
})
const deltaAt = computed(() => {
  const d = delta.value
  const i = scrubber.q
  return d ? { v: d.p50[i], lo: d.p10?.[i], hi: d.p90?.[i] } : null
})
function isHeadline(k: NationalMetric): k is HeadlineMetric {
  return (HEADLINE_METRICS as string[]).includes(k)
}
/** headline deltas at the scrubber quarter with compare confidence at the reference quarter */
const headlineDeltas = computed(() =>
  HEADLINE_METRICS.map((m) => {
    const d = results.compare?.delta.series[m]
    const i = scrubber.q
    return {
      m,
      label: HEADLINE_LABELS[m],
      def: metricDef(m),
      v: d?.p50[i],
      lo: d?.p10?.[i],
      hi: d?.p90?.[i],
      conf: results.compare?.confidence[m]?.[refQ.value],
    }
  }),
)
const diff = computed(() => results.compare?.diff ?? results.docB?.explain.diff ?? [])

// ----- delta map -----
const stateDeltas = computed(() => {
  const m = new Map<string, StateValue>()
  for (const s of results.compare?.delta.states ?? [])
    m.set(s.fips, { value: s.employment_pct_vs_baseline.p50[scrubber.q] })
  return m
})
const mapDomain = computed<[number, number]>(() => {
  const all: number[] = []
  for (const s of results.compare?.delta.states ?? []) all.push(...s.employment_pct_vs_baseline.p50)
  return niceSymmetric(symmetricDomain(all))
})
const mapColor = computed(() => divergingScale(mapDomain.value, theme.mode))

// ----- top ±10 occupations by displacement delta -----
const byCode = computed(() => new Map(results.occupations.map((o) => [o.occ_code, o])))
const occRows = computed<DeltaRow[]>(() => {
  const rows = (results.compare?.delta.occupations ?? [])
    .map((o) => ({
      key: o.occ_code,
      label: byCode.value.get(o.occ_code)?.title ?? o.occ_code,
      value: o.displacement.p50[scrubber.q] ?? 0,
      extra: [
        { label: 'A displaced', value: fmtShare(byCode.value.get(o.occ_code)?.displacement.p50[scrubber.q], 1) },
        {
          label: 'B displaced',
          value: fmtShare(
            results.docB?.occupations.find((x) => x.occ_code === o.occ_code)?.displacement.p50[scrubber.q],
            1,
          ),
        },
      ],
    }))
    .filter((r) => r.value !== 0)
  rows.sort((a, b) => b.value - a.value)
  const top = rows.slice(0, 10)
  const bottom = rows.slice(-10).filter((r) => !top.includes(r))
  return [...top, ...bottom]
})

// ----- why: trace differences -----
const traceMetric = computed<HeadlineMetric>(() =>
  isHeadline(metric.value) ? metric.value : 'employment_pct_vs_baseline',
)
const traceRows = computed(() => {
  const a = results.trace[traceMetric.value]?.[refQ.value]
  const b = results.docB?.explain.trace?.[traceMetric.value]?.[refQ.value]
  if (!a || !b) return []
  return (Object.keys(TRACE_LABELS) as TraceKey[])
    .map((k) => ({ k, label: TRACE_LABELS[k], a: a[k], b: b[k], d: b[k] - a[k] }))
    .filter((r) => Number.isFinite(r.d))
})
const traceStory = computed(() => {
  const r = traceRows.value
  if (!r.length) return ''
  const pick = (k: TraceKey) => r.find((x) => x.k === k)
  const ad = pick('adoption_emp')
  const dd = pick('realized_D')
  const cost = pick('dln_unit_cost')
  const parts: string[] = []
  if (ad) parts.push(`adoption ${ad.d >= 0 ? '+' : '−'}${Math.abs(ad.d * 100).toFixed(1)} pp`)
  if (cost) parts.push(`unit cost ${cost.d <= 0 ? 'lower' : 'higher'} by ${Math.abs(cost.d * 100).toFixed(1)}%`)
  if (dd) parts.push(`displacement ${dd.d >= 0 ? '+' : '−'}${Math.abs(dd.d * 100).toFixed(2)} pp of 2023 jobs`)
  return parts.join(' → ')
})
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>
        A: <span class="a">{{ results.scenarioName }}</span> vs B:
        <span class="b">{{ results.compareName ?? '—' }}</span>
      </h2>
      <span v-if="results.compareLoading" class="muted">Comparing…</span>
    </div>
    <div class="filters">
      <label class="muted">
        Scenario B
        <select class="select" :value="results.compareId ?? ''" @change="onPickB">
          <option value="">— pick —</option>
          <template v-for="g in groups" :key="g.label">
            <optgroup v-if="g.items.length" :label="g.label">
              <option v-for="s in g.items" :key="s.id" :value="s.id" :disabled="s.id === results.scenarioId">
                {{ s.name }}
              </option>
            </optgroup>
          </template>
        </select>
      </label>
      <button class="btn" :disabled="!results.compareId" @click="swap">Swap</button>
      <label class="muted">
        Metric
        <select v-model="metric" class="select">
          <option v-for="m in COMPARE_METRICS" :key="m.key" :value="m.key">{{ m.def.label }}</option>
        </select>
      </label>
      <span class="chart-note">Deltas are paired across draws (same seed), so the band is meaningful.</span>
    </div>

    <div v-if="results.docB && results.compare" class="grid">
      <div class="card block changed">
        <h3>What changed <span class="muted">({{ diff.length }})</span></h3>
        <p v-if="!diff.length" class="muted small">No canonical diff between these runs.</p>
        <ul v-else class="diff">
          <li v-for="d in diff" :key="d.path">
            <code>{{ d.path.replace(/^levers\./, '') }}</code>
            <span class="mono">{{ fmtLeverValue(d.from) }} → <strong>{{ fmtLeverValue(d.to) }}</strong></span>
            <span class="muted mech">{{ d.mechanism }}</span>
          </li>
        </ul>
      </div>

      <div class="card block panel">
        <h3><span class="sw" :style="{ background: hueA }"></span>A · {{ def.label }}</h3>
        <SeriesChart
          v-if="seriesA"
          :series="seriesA"
          :quarters="results.quarters"
          :q="scrubber.q"
          :hue="hueA"
          :label="def.label"
          :format="(v) => def.format(v)"
          :axis-format="def.axisFormat"
          :zero="def.polarity === 'diverging'"
          :y-domain="yDomain"
          :height="240"
          @scrub="scrubber.set($event)"
        />
      </div>
      <div class="card block panel">
        <h3><span class="sw" :style="{ background: hueB }"></span>B · {{ def.label }}</h3>
        <SeriesChart
          v-if="seriesB"
          :series="seriesB"
          :quarters="results.quarters"
          :q="scrubber.q"
          :hue="hueB"
          :label="def.label"
          :format="(v) => def.format(v)"
          :axis-format="def.axisFormat"
          :zero="def.polarity === 'diverging'"
          :y-domain="yDomain"
          :height="240"
          @scrub="scrubber.set($event)"
        />
      </div>

      <div class="card block strip">
        <div class="strip-head">
          <h3>Δ (B − A) · {{ def.label }}</h3>
          <span v-if="deltaAt" class="delta-now">
            <strong class="mono">{{ def.format(deltaAt.v) }}</strong>
            <span v-if="deltaAt.lo != null" class="mono muted"
              >[{{ def.format(deltaAt.lo) }}, {{ def.format(deltaAt.hi) }}]</span
            >
            <span class="muted">at {{ qLabel }}</span>
          </span>
        </div>
        <SeriesChart
          v-if="delta"
          :series="delta"
          :quarters="results.quarters"
          :q="scrubber.q"
          :hue="hueB"
          :label="`Δ ${def.label}`"
          :format="(v) => def.format(v)"
          :axis-format="def.axisFormat"
          zero
          :height="180"
          @scrub="scrubber.set($event)"
        />
        <ul class="headlines">
          <li v-for="h in headlineDeltas" :key="h.m">
            <span class="hl">{{ h.label }}</span>
            <strong class="mono">{{ h.def.format(h.v) }}</strong>
            <span v-if="h.lo != null" class="mono muted">[{{ h.def.format(h.lo) }}, {{ h.def.format(h.hi) }}]</span>
            <ConfidenceGlyph :confidence="h.conf" :at="refQ" with-label />
          </li>
        </ul>
      </div>

      <div class="card block map">
        <h3>Δ net employment by state, {{ qLabel }}</h3>
        <div class="map-box">
          <ChoroplethMap
            v-if="results.geo"
            :geo="results.geo"
            :values="stateDeltas"
            :color="mapColor"
            :format="(v) => fmtPct(v)"
            metric-label="Δ net employment (B − A)"
            :selected="scrubber.state"
            @select="scrubber.selectState($event)"
          />
        </div>
        <ColorLegend
          :color="mapColor"
          :domain="mapDomain"
          :format="(v) => fmtPct(v, 1)"
          title="Δ employment, pp of baseline employment"
          diverging
        />
      </div>

      <div class="card block occ">
        <h3>Top ±10 occupations by Δ displacement, {{ qLabel }}</h3>
        <DeltaBars
          :rows="occRows"
          :format="(v) => fmtShare(v, 2)"
          :axis-format="(v) => fmtShare(v, 1)"
          :mode="theme.mode"
          title="Occupations by displacement delta"
          negative-label="Less displaced in B"
          positive-label="More displaced in B"
        />
      </div>

      <div class="card block why">
        <h3>Why · trace at {{ quarterLabel(refQ) }} <span class="muted">({{ HEADLINE_LABELS[traceMetric] }})</span></h3>
        <p v-if="traceStory" class="story">{{ traceStory }}</p>
        <table v-if="traceRows.length" class="data">
          <thead>
            <tr>
              <th>Quantity</th>
              <th class="num">A</th>
              <th class="num">B</th>
              <th class="num">Δ</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in traceRows" :key="r.k" :class="{ hot: Math.abs(r.d) > 1e-6 }">
              <td>{{ r.label }}</td>
              <td class="num">{{ r.a }}</td>
              <td class="num">{{ r.b }}</td>
              <td class="num" :class="{ muted: Math.abs(r.d) <= 1e-6 }">{{ r.d >= 0 ? '+' : '' }}{{ Number(r.d.toFixed(4)) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted small">No trace published for this metric in one of the runs.</p>
      </div>
    </div>
    <div v-else class="card empty">
      <p class="muted">
        {{ results.compareLoading ? 'Loading scenario B…' : 'Pick a scenario B to compare.' }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.a {
  color: var(--ink);
}
.b {
  color: var(--ink);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: start;
}
.block {
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.block h3 {
  font-size: 14px;
  color: var(--ink-2);
  display: flex;
  align-items: center;
  gap: 8px;
}
.changed,
.strip {
  grid-column: 1 / -1;
}
.sw {
  width: 12px;
  height: 3px;
  border-radius: 2px;
  display: inline-block;
}
.diff {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 8px 16px;
  font-size: 14px;
}
.diff li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow-wrap: anywhere;
}
.diff code {
  font-size: 13px;
  background: var(--surface-2);
  padding: 1px 6px;
  border-radius: 4px;
  align-self: flex-start;
}
.mech {
  font-size: 13px;
}
.small {
  font-size: 14px;
  margin: 0;
}
.strip-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.delta-now {
  display: inline-flex;
  gap: 8px;
  align-items: baseline;
  font-size: 15px;
}
.delta-now strong {
  font-size: 20px;
}
.headlines {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  font-size: 14px;
}
.headlines li {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.hl {
  color: var(--ink-2);
  min-width: 110px;
}
.map-box {
  height: 380px;
}
.story {
  margin: 0;
  font-size: 14px;
  padding: 8px 10px;
  background: var(--surface-2);
  border-radius: 6px;
}
tr.hot td {
  color: var(--ink);
}
.empty {
  padding: 28px;
}
@media (max-width: 1000px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
