<script setup lang="ts">
import { computed, ref } from 'vue'
import { line as d3line, scaleLinear } from 'd3'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useRegionStore } from '@/stores/region'
import { fmtCompact, fmtShare, fmtUsd, quarterLabel } from '@/lib/format'
import {
  APPLICATION_FAMILY_LABELS,
  TABLE_QUARTERS,
  applicationRegion,
  displacementTable,
  gateMarkers,
  hourlyWage,
  meanWage,
  quarterPosition,
  targetTitles,
  type GateMarker,
} from '@/lib/applications'
import {
  EMBODIMENT_CLASSES,
  EMBODIMENT_CLASS_LABELS,
  REGION_NAMES,
  isEmbodimentClass,
  isRegionId,
  type ApplicationEntry,
  type ApplicationRegion,
} from '@/types/results'
import GateTimeline from '@/components/charts/GateTimeline.vue'

/**
 * Phase 6 (spec v0.3 §A.6.4, contracts §20): one row per catalogue application for the selected
 * region, with the embodiment-class strip above. Regions without a `by_region` entry, and World
 * (no application split), read the U.S. block and say so.
 */
const results = useResultsStore()
const scrubber = useScrubberStore()
const regionStore = useRegionStore()

const q = computed(() => scrubber.q)
const qLabel = computed(() => quarterLabel(results.quarters[q.value]))
const apps = computed<ApplicationEntry[]>(() => results.doc?.applications ?? [])
const regionName = (id: string) => (isRegionId(id) ? REGION_NAMES[id] : id)
const classLabel = (c: string) => (isEmbodimentClass(c) ? EMBODIMENT_CLASS_LABELS[c] : c)

/** the series block behind the class strip: the selected region, else the U.S. */
const seriesRegion = computed(() => {
  const id = regionStore.isWorld ? 'US' : regionStore.region
  return results.doc?.series[id] ? id : 'US'
})
const regionNote = computed(() => {
  if (regionStore.isWorld) return 'World has no application split — showing the U.S.'
  if (seriesRegion.value !== regionStore.region)
    return `No series for ${regionStore.label} in this run — showing the U.S.`
  return ''
})
const wageHourly = computed(() => hourlyWage(meanWage(results.occupations)))
const nowX = computed(() => quarterPosition(results.quarters[q.value]))

// ----- embodiment classes strip -----
const classes = computed(() => {
  const emb = results.supply?.embodiment
  if (!emb) return []
  const blk = results.doc?.series[seriesRegion.value]
  const i = q.value
  return EMBODIMENT_CLASSES.filter((c) => emb[c]).map((c) => {
    const e = emb[c]!
    const fleet = blk?.fleet_stock?.[c]
    const cov = blk?.coverage?.[c]
    const appr = blk?.approval_share?.[c]
    return {
      cls: c,
      label: EMBODIMENT_CLASS_LABELS[c],
      clock: e.clock.p50[i],
      price: e.unit_price_usd.p50[i],
      cph: e.cost_per_hour_usd.p50[i],
      fleet: fleet?.p50[i],
      fleetLo: fleet?.p10?.[i],
      fleetHi: fleet?.p90?.[i],
      coverage: cov?.p50[i],
      approval: appr?.central?.[i] ?? appr?.p50[i],
    }
  })
})
const fmtCph = (v: number | null | undefined) =>
  v == null || !Number.isFinite(v) ? '—' : `$${v.toFixed(2)}/h`
const fmtDisp = (v: number | null | undefined) =>
  v == null || !Number.isFinite(v) ? '—' : `${v.toFixed(v < 10 ? 2 : 1)}%`
const fleetBand = (lo?: number, hi?: number) =>
  lo != null && hi != null ? `10–90 band: ${fmtCompact(lo)} to ${fmtCompact(hi)} units` : ''
const pct = (v?: number | null) => `${Math.round(100 * Math.min(1, Math.max(0, v ?? 0)))}%`

// ----- application rows -----
interface Row {
  app: ApplicationEntry
  block: ApplicationRegion | null
  region: string
  fallback: boolean
  markers: GateMarker[]
  disp: number | undefined
  cov: number | undefined
  appr: number | undefined
  spark: string
  dot: { x: number; y: number } | null
}
const SPARK_W = 120
const SPARK_H = 30
const rows = computed<Row[]>(() => {
  const pre = apps.value.map((app) => ({ app, ...applicationRegion(app, regionStore.region) }))
  // one shared y scale so the sparklines compare across rows
  const max = Math.max(1, ...pre.flatMap((p) => p.block?.displacement_share ?? [0]))
  const n = results.quarters.length
  const x = scaleLinear()
    .domain([0, Math.max(1, n - 1)])
    .range([2, SPARK_W - 2])
  const y = scaleLinear().domain([0, max]).range([SPARK_H - 3, 3])
  const gen = d3line<number>()
    .x((_, i) => x(i))
    .y((v) => y(v))
  const i = q.value
  return pre.map((p) => {
    const ds = p.block?.displacement_share ?? []
    const v = ds[i]
    return {
      app: p.app,
      block: p.block,
      region: p.region,
      fallback: p.fallback,
      markers: gateMarkers(p.block?.first_quarter),
      disp: v,
      cov: p.block?.coverage[i],
      appr: p.block?.approval[i],
      spark: p.block ? (gen(ds) ?? '') : '',
      dot: v == null ? null : { x: x(i), y: y(v) },
    }
  })
})
const anyFallback = computed(() => rows.value.some((r) => r.fallback))

const expanded = ref<string | null>(null)
function toggle(id: string) {
  expanded.value = expanded.value === id ? null : id
}
const detail = computed(() => {
  const row = rows.value.find((r) => r.app.app_id === expanded.value)
  if (!row) return null
  return {
    row,
    targets: targetTitles(row.app.occ_codes, results.occupations),
    table: displacementTable(row.app, results.quarters),
    gates: row.markers.map((m) => `${m.label} ${m.missing ? 'not by 2040' : quarterLabel(m.quarter ?? '')}`),
  }
})
</script>

<template>
  <section class="card apps" aria-labelledby="apps-title">
    <div class="head">
      <h3 id="apps-title">Applications, {{ regionNote || anyFallback ? 'U.S.' : regionStore.label }}, {{ qLabel }}</h3>
      <span v-if="regionNote" class="badge composition" :title="regionNote">{{ regionNote }}</span>
      <span class="chart-note">
        Embodied automation by catalogue application (spec v0.3 §A.8): the gates each application
        passes in the region, its displacement share over time and where its class stands on
        coverage and approval. Click a row for the catalogue entry and every region.
      </span>
    </div>

    <div v-if="classes.length" class="classes" role="list" aria-label="Embodiment classes">
      <div v-for="c in classes" :key="c.cls" class="cls" role="listitem">
        <div class="cls-head">
          <strong>{{ c.label }}</strong>
          <span class="muted mono">{{ c.clock == null ? '—' : c.clock.toFixed(1) }} doublings</span>
        </div>
        <dl class="cls-facts">
          <dt>Unit price</dt>
          <dd class="mono">{{ fmtUsd(c.price) }}</dd>
          <dt>Cost per hour</dt>
          <dd>
            <span class="mono">{{ fmtCph(c.cph) }}</span>
            <span class="muted small vs">vs {{ fmtCph(wageHourly) }} U.S. mean wage</span>
          </dd>
          <dt>Fleet, {{ seriesRegion }}</dt>
          <dd class="mono" :title="fleetBand(c.fleetLo, c.fleetHi)">
            {{ c.fleet == null ? '—' : fmtCompact(c.fleet) }}
            <span v-if="c.fleetLo != null" class="muted small">units</span>
          </dd>
        </dl>
        <div class="bars">
          <div class="bar-row" :title="`Coverage of the class's task-hours, ${qLabel}`">
            <span class="muted">coverage</span>
            <span class="bar"><span class="fill" :style="{ width: pct(c.coverage) }"></span></span>
            <span class="mono">{{ fmtShare(c.coverage) }}</span>
          </div>
          <div class="bar-row" :title="`Approved share J, ${qLabel}`">
            <span class="muted">approval</span>
            <span class="bar"><span class="fill approval" :style="{ width: pct(c.approval) }"></span></span>
            <span class="mono">{{ fmtShare(c.approval) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="rows" role="table" aria-label="Applications">
      <div class="row hdr" role="row">
        <div role="columnheader">Application</div>
        <div role="columnheader" class="num">Target jobs 2024</div>
        <div role="columnheader" class="gates-hdr">
          <span>Gates</span>
          <GateTimeline years :height="18" />
        </div>
        <div role="columnheader">Displacement share</div>
        <div role="columnheader">Coverage · approval</div>
      </div>
      <template v-for="r in rows" :key="r.app.app_id">
        <div
          class="row"
          :class="{ open: expanded === r.app.app_id }"
          role="row"
          tabindex="0"
          :aria-expanded="expanded === r.app.app_id"
          @click="toggle(r.app.app_id)"
          @keydown.enter.prevent="toggle(r.app.app_id)"
          @keydown.space.prevent="toggle(r.app.app_id)"
        >
          <div class="c-name" role="cell">
            <span class="name">{{ r.app.name }}</span>
            <span class="chips">
              <span class="chip">{{ APPLICATION_FAMILY_LABELS[r.app.family] ?? r.app.family }}</span>
              <span v-for="c in r.app.classes" :key="c" class="chip cls">{{ classLabel(c) }}</span>
              <span v-if="r.app.platform" class="chip platform" title="Target workers are largely self-employed or platform workers">platform</span>
              <span v-if="r.fallback && !regionNote" class="chip muted-chip" :title="`No ${regionStore.label} entry — U.S. shown`">U.S.</span>
            </span>
          </div>
          <div class="c-emp mono num" role="cell">{{ fmtCompact(r.block?.target_employment_2024) }}</div>
          <div class="c-gates" role="cell">
            <GateTimeline :markers="r.markers" :current="nowX" />
          </div>
          <div class="c-spark" role="cell">
            <svg :width="SPARK_W" :height="SPARK_H" aria-hidden="true">
              <path :d="r.spark" fill="none" class="spark" stroke-width="1.5" />
              <line v-if="r.dot" class="spark-now" :x1="r.dot.x" :x2="r.dot.x" y1="2" :y2="SPARK_H - 2" />
              <circle v-if="r.dot" :cx="r.dot.x" :cy="r.dot.y" r="3.5" class="spark-dot" />
            </svg>
            <strong class="mono">{{ fmtDisp(r.disp) }}</strong>
          </div>
          <div class="c-bars" role="cell">
            <div class="bar-row" :title="`Coverage, ${qLabel}`">
              <span class="bar"><span class="fill" :style="{ width: pct(r.cov) }"></span></span>
              <span class="mono">{{ fmtShare(r.cov) }}</span>
            </div>
            <div class="bar-row" :title="`Approved share J, ${qLabel}`">
              <span class="bar"><span class="fill approval" :style="{ width: pct(r.appr) }"></span></span>
              <span class="mono">{{ fmtShare(r.appr) }}</span>
            </div>
          </div>
        </div>
        <div v-if="expanded === r.app.app_id && detail" class="detail" role="row">
          <div class="detail-grid" role="cell">
            <div>
              <h4>Target occupations</h4>
              <ul class="targets">
                <li v-for="t in detail.targets" :key="t.code">
                  <code>{{ t.code }}</code>
                  <span :class="{ muted: !t.title }">{{ t.title ?? 'not in this run’s occupation table' }}</span>
                </li>
              </ul>
              <h4>Regions first</h4>
              <p>{{ r.app.regions_first.map(regionName).join(', ') }}</p>
            </div>
            <div>
              <h4>Anchor series</h4>
              <p>{{ r.app.anchor }}</p>
              <h4>Binding constraints</h4>
              <p>{{ r.app.constraints }}</p>
              <h4>Gates in {{ regionName(r.region) }}</h4>
              <p>{{ detail.gates.join(' · ') }}</p>
            </div>
            <div>
              <h4>
                Catalogue timing
                <span class="badge fixture" title="Provisional central ranges from the catalogue; expert estimates pending verification (spec v0.3 §A.8)">provisional, E, V?</span>
              </h4>
              <dl class="prov">
                <dt>Profitable at U.S. wages</dt>
                <dd class="mono">{{ r.app.provisional_profitable }}</dd>
                <dt>Deployed at 50% coverage</dt>
                <dd class="mono">{{ r.app.provisional_deployed50 }}</dd>
              </dl>
              <p class="chart-note">Ranges are inputs to attack, not results.</p>
            </div>
            <div class="tbl">
              <h4>Displacement share by region <span class="muted">(central, % of target task-hours)</span></h4>
              <table class="data compact">
                <thead>
                  <tr>
                    <th>Region</th>
                    <th v-for="qk in TABLE_QUARTERS" :key="qk" class="num">{{ quarterLabel(qk) }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="t in detail.table" :key="t.region" :class="{ sel: t.region === r.region }">
                    <td :title="regionName(t.region)">{{ t.region }}</td>
                    <td v-for="(v, i) in t.values" :key="i" class="num">{{ fmtDisp(v) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>
    </div>
    <p class="chart-note">
      Gates: <span class="glyph g1"></span> 1% of the target task-hours displaced,
      <span class="glyph g10"></span> 10%, <span class="glyph g50"></span> 50% coverage; hollow markers
      past the axis = not by 2040. The vertical tick is the scrubber. Sparkline = displacement share
      (central run, one scale for all rows); bars = coverage and approved share J at {{ qLabel }}.
      Class figures are the median draw; cost per hour compares with the employment-weighted
      2023 U.S. mean wage at 2,080 h/yr.
    </p>
  </section>
</template>

<style scoped>
.apps {
  padding: 10px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.badge.composition {
  background: var(--surface-2);
  color: var(--ink-2);
}
.small {
  font-size: 13px;
}
/* class strip */
.classes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 10px;
}
.cls {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  min-width: 0;
}
.cls-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.cls-facts {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 10px;
}
.cls-facts dt {
  color: var(--muted);
}
.cls-facts dd {
  margin: 0;
  text-align: right;
}
.cls-facts .vs {
  display: block;
  line-height: 1.2;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.bar-row {
  display: grid;
  grid-template-columns: auto 1fr 44px;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.bar-row > .mono {
  text-align: right;
}
.cls .bar-row > .muted {
  min-width: 62px;
}
.bar {
  display: block;
  height: 5px;
  border-radius: 3px;
  background: var(--surface-2);
  overflow: hidden;
}
.fill {
  display: block;
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width var(--t);
}
.fill.approval {
  background: var(--ink-2);
}
/* rows */
.rows {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--grid);
}
.row {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) 92px minmax(200px, 1.6fr) 190px 150px;
  gap: 0 14px;
  align-items: center;
  padding: 7px 4px;
  border-bottom: 1px solid var(--grid);
  min-width: 0;
  font-size: 14px;
}
.row:not(.hdr) {
  cursor: pointer;
}
.row:not(.hdr):hover,
.row.open {
  background: var(--surface-2);
}
.row.hdr {
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
  padding-top: 6px;
  padding-bottom: 4px;
}
.gates-hdr {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.num {
  text-align: right;
}
.c-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.name {
  font-weight: 600;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.chip {
  font-size: 12px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--ink-2);
  border: 1px solid var(--border);
  line-height: 18px;
}
.row.open .chip,
.row:hover .chip {
  background: var(--surface);
}
.chip.cls {
  color: var(--ink);
}
.chip.platform {
  border-style: dashed;
}
.chip.muted-chip {
  color: var(--muted);
}
.c-gates {
  min-width: 0;
}
.c-spark {
  display: flex;
  align-items: center;
  gap: 8px;
}
.spark {
  stroke: var(--accent);
}
.spark-now {
  stroke: var(--ink-2);
  stroke-width: 1;
}
.spark-dot {
  fill: var(--accent);
  stroke: var(--surface);
  stroke-width: 1.5;
}
.c-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.c-bars .bar-row {
  grid-template-columns: 1fr 44px;
}
/* detail */
.detail {
  border-bottom: 1px solid var(--grid);
  padding: 10px 6px 12px;
  background: var(--surface);
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1.1fr 1fr 1.5fr;
  gap: 10px 22px;
  font-size: 14px;
}
@media (max-width: 1100px) {
  .detail-grid {
    grid-template-columns: 1fr 1fr;
  }
  .tbl {
    grid-column: 1 / -1;
  }
}
@media (max-width: 640px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
.detail h4 {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.detail h4 + p,
.detail p {
  margin: 0 0 8px;
}
.targets {
  list-style: none;
  padding: 0;
  margin: 0 0 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.targets li {
  display: flex;
  gap: 8px;
  align-items: baseline;
}
.targets code {
  font-size: 13px;
  background: var(--surface-2);
  padding: 0 5px;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
}
.prov {
  margin: 0 0 6px;
  display: grid;
  grid-template-columns: auto auto;
  gap: 2px 12px;
}
.prov dt {
  color: var(--ink-2);
}
.prov dd {
  margin: 0;
}
.tbl {
  min-width: 0;
  overflow: auto;
}
table.compact {
  font-size: 13px;
}
table.compact td,
table.compact th {
  padding: 3px 8px;
}
tr.sel td {
  font-weight: 600;
}
/* legend glyphs */
.glyph {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--ink);
  vertical-align: middle;
  margin: 0 2px;
}
.glyph.g1 {
  width: 7px;
  height: 7px;
}
.glyph.g10 {
  background: var(--accent);
  width: 11px;
  height: 11px;
}
.glyph.g50 {
  border-radius: 0;
  background: var(--surface);
  border: 1.5px solid var(--ink);
  transform: rotate(45deg);
  width: 8px;
  height: 8px;
}
@media (max-width: 1000px) {
  .row {
    grid-template-columns: minmax(180px, 1fr) 80px minmax(160px, 1fr);
  }
  .c-spark,
  .c-bars,
  .row.hdr > :nth-child(4),
  .row.hdr > :nth-child(5) {
    display: none;
  }
}
</style>
