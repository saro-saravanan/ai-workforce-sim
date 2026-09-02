<script setup lang="ts">
import { computed, watch } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useRegionStore } from '@/stores/region'
import { useThemeStore } from '@/stores/theme'
import {
  STATE_METRICS,
  STATE_METRIC_KEYS,
  WORLD_METRICS,
  mapMetricDef,
  type MapMetric,
} from '@/lib/metrics'
import {
  divergingScale,
  magnitudeDomain,
  niceSymmetric,
  sequentialScale,
  symmetricDomain,
} from '@/lib/scales'
import { quarterLabel } from '@/lib/format'
import {
  REGION_NAMES,
  isRegionId,
  type Series,
  type StateMetric,
  type StateResult,
  type WorldMetric,
} from '@/types/results'
import ChoroplethMap, { type StateValue } from '@/components/charts/ChoroplethMap.vue'
import WorldMap, { type CountryValue } from '@/components/charts/WorldMap.vue'
import ColorLegend from '@/components/charts/ColorLegend.vue'
import SparkLine from '@/components/charts/SparkLine.vue'
import { CATEGORICAL } from '@/lib/palette'

const results = useResultsStore()
const scrubber = useScrubberStore()
const regionStore = useRegionStore()
const theme = useThemeStore()
results.loadWorldGeo()
watch(
  () => regionStore.region,
  (r) => {
    if (r === 'US') results.loadGeo()
  },
  { immediate: true },
)

/** world: the globe; states: the U.S. state map; region: a region zoom (EU members or one country) */
const level = computed(() =>
  regionStore.isWorld ? 'world' : regionStore.region === 'US' ? 'states' : 'region',
)
const worldKeys = Object.keys(WORLD_METRICS) as Array<keyof typeof WORLD_METRICS>
const metricOptions = computed<MapMetric[]>(() =>
  level.value === 'states' ? STATE_METRIC_KEYS : worldKeys,
)
/** the URL metric, or employment when it does not apply at this level */
const metric = computed<MapMetric>(() =>
  (metricOptions.value as string[]).includes(scrubber.metric)
    ? scrubber.metric
    : 'employment_pct_vs_baseline',
)
const def = computed(() => mapMetricDef(metric.value))
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const regionName = (id: string) => (isRegionId(id) ? REGION_NAMES[id] : id)

/** Series behind a region's colour: the region's rents total, or its member entries' slim series. */
function regionSeries(id: string): Series | undefined {
  const rs = results.doc?.series[id]
  if (metric.value === 'ai_rents_received_bn') return rs?.ai_rents_received_bn?.total
  return rs?.[metric.value as Exclude<MapMetric, 'ai_rents_received_bn'>]
}

/** Domain over ALL quarters so the legend is stable while scrubbing. */
const domain = computed<[number, number]>(() => {
  const all: number[] = []
  if (level.value === 'states') {
    for (const s of results.states) for (const v of s[metric.value as StateMetric].p50) all.push(v)
  } else {
    for (const id of results.regionIds) for (const v of regionSeries(id)?.p50 ?? []) all.push(v)
  }
  return def.value.polarity === 'diverging'
    ? niceSymmetric(symmetricDomain(all))
    : magnitudeDomain(all)
})
const color = computed(() =>
  def.value.polarity === 'diverging'
    ? divergingScale(domain.value, theme.mode)
    : sequentialScale(
        domain.value,
        theme.mode,
        metric.value === 'ai_rents_received_bn' ? 'blue' : 'red',
      ),
)

// ----- states level (unchanged from Phase 1) -----
const stateValues = computed(() => {
  const m = new Map<string, StateValue>()
  for (const s of results.states) {
    const ser = s[metric.value as StateMetric]
    m.set(s.fips, { value: ser.p50[scrubber.q], lo: ser.p10?.[scrubber.q], hi: ser.p90?.[scrubber.q] })
  }
  return m
})
const byFips = computed(() => new Map(results.states.map((s) => [s.fips, s])))
function stateExtra(fips: string) {
  const s = byFips.value.get(fips)
  if (!s) return []
  return STATE_METRIC_KEYS.filter((k) => k !== metric.value).map((k) => ({
    label: STATE_METRICS[k].short,
    value: STATE_METRICS[k].format(s[k].p50[scrubber.q]),
  }))
}
const selectedState = computed<StateResult | undefined>(() =>
  scrubber.state ? byFips.value.get(scrubber.state) : undefined,
)

// ----- world / region level -----
const countryValues = computed(() => {
  const m = new Map<string, CountryValue>()
  const i = scrubber.q
  for (const w of results.world) {
    const ser =
      metric.value === 'ai_rents_received_bn'
        ? regionSeries(w.region_id)
        : w[metric.value as WorldMetric]
    if (!ser) continue
    m.set(w.iso3, { value: ser.p50[i], lo: ser.p10?.[i], hi: ser.p90?.[i] })
  }
  return m
})
const fixtureRegions = computed(
  () => new Set(results.regionIds.filter((id) => results.isRegionFixture(id))),
)
const fixtureNames = computed(() => [...fixtureRegions.value].map(regionName).join(', '))
function countryExtra(_iso3: string, region: string) {
  const rs = results.doc?.series[region]
  const i = scrubber.q
  const rows = []
  for (const k of worldKeys) {
    if (k === metric.value) continue
    const ser = k === 'ai_rents_received_bn' ? rs?.ai_rents_received_bn?.total : rs?.[k]
    if (ser) rows.push({ label: WORLD_METRICS[k].short, value: WORLD_METRICS[k].format(ser.p50[i]) })
  }
  if (region === 'EU') rows.push({ label: 'Member data', value: 'region composition' })
  return rows
}
const selectedMember = computed(() =>
  regionStore.member ? results.world.find((w) => w.iso3 === regionStore.member) : undefined,
)
/** the detail card for a region drill: the member (EU) or the whole region (single-country regions) */
const detail = computed(() => {
  if (level.value !== 'region') return null
  const rs = results.doc?.series[regionStore.region]
  if (!rs) return null
  const member = selectedMember.value
  if (regionStore.region === 'EU' && !member) return null
  return {
    title: member?.name ?? regionStore.label,
    sub: member
      ? `${regionStore.label} member · ${qLabel.value}`
      : `Region · ${qLabel.value}`,
    composition: regionStore.region === 'EU',
    rows: worldKeys
      .map((k) => ({
        k,
        def: WORLD_METRICS[k],
        series: k === 'ai_rents_received_bn' ? rs.ai_rents_received_bn?.total : rs[k],
      }))
      .filter((r): r is typeof r & { series: Series } => !!r.series),
  }
})
const total = computed(() => {
  const ser =
    metric.value === 'ai_rents_received_bn'
      ? results.rents?.total
      : results.series?.[metric.value as Exclude<MapMetric, 'ai_rents_received_bn'>]
  return ser ? def.value.format(ser.p50[scrubber.q]) : '—'
})
const hue = computed(() => CATEGORICAL[theme.mode][0] ?? '#2a78d6')
const crumbRegion = computed(() => (level.value === 'world' ? null : regionStore.label))
const crumbLeaf = computed(() =>
  level.value === 'states' ? selectedState.value?.name : selectedMember.value?.name,
)

function setMetric(k: MapMetric) {
  scrubber.setMetric(k)
}
function goWorld() {
  regionStore.setRegion('world')
  scrubber.selectState(null)
}
function goRegion() {
  regionStore.selectMember(null)
  scrubber.selectState(null)
}
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>{{ def.label }}{{ def.polarity === 'diverging' ? ' vs baseline' : '' }}, {{ qLabel }}</h2>
      <nav class="crumbs" aria-label="Breadcrumb">
        <button class="crumb" :class="{ current: !crumbRegion }" @click="goWorld">World</button>
        <template v-if="crumbRegion">
          <span class="muted">›</span>
          <button class="crumb" :class="{ current: !crumbLeaf }" @click="goRegion">
            {{ crumbRegion }}
          </button>
        </template>
        <template v-if="crumbLeaf">
          <span class="muted">›</span>
          <span class="crumb current">{{ crumbLeaf }}</span>
        </template>
      </nav>
      <span
        v-if="level === 'states' && results.isFixture"
        class="badge fixture"
        title="occ_state is a fixture: same occupational mix in every state"
        >fixture data</span
      >
      <span
        v-if="level === 'region' && regionStore.region === 'EU'"
        class="badge composition"
        title="meta.data_flags.members: members carry their region's series until member-level data exists"
        >member data = region composition</span
      >
      <span
        v-if="level === 'region' && fixtureRegions.has(regionStore.region)"
        class="badge fixture"
        title="occ_region is a structural proxy (FIXTURE) for this region"
        >imputed composition</span
      >
    </div>
    <div class="filters">
      <span class="muted">Metric</span>
      <div class="seg" role="group" aria-label="Metric">
        <button
          v-for="k in metricOptions"
          :key="k"
          class="btn"
          :aria-pressed="metric === k"
          @click="setMetric(k)"
        >
          {{ mapMetricDef(k).short }}
        </button>
      </div>
      <span class="muted"
        >{{ regionStore.label }} total: <strong class="mono">{{ total }}</strong></span
      >
      <span v-if="level === 'world'" class="chart-note">
        Click a region to drill: US → states, EU → members, others → country.
      </span>
    </div>
    <div class="map-layout">
      <div class="card map-card">
        <template v-if="level === 'states'">
          <ChoroplethMap
            v-if="results.geo"
            :geo="results.geo"
            :values="stateValues"
            :color="color"
            :format="def.format"
            :metric-label="def.label"
            :selected="scrubber.state"
            :extra="stateExtra"
            @select="scrubber.selectState($event)"
          />
          <p v-else class="muted loading">Loading state geometry…</p>
        </template>
        <template v-else>
          <WorldMap
            v-if="results.worldGeo"
            :geo="results.worldGeo"
            :focus="regionStore.region"
            :values="countryValues"
            :color="color"
            :format="def.format"
            :metric-label="def.label"
            :region-name="regionName"
            :fixture-regions="fixtureRegions"
            :selected="regionStore.member"
            :extra="countryExtra"
            @select-region="regionStore.setRegion($event)"
            @select-member="regionStore.selectMember($event)"
          />
          <p v-else class="muted loading">Loading world geometry…</p>
        </template>
        <div class="legend-row">
          <ColorLegend
            :color="color"
            :domain="domain"
            :format="def.axisFormat"
            :title="`${def.label} · ${def.unit}`"
            :diverging="def.polarity === 'diverging'"
          />
          <div v-if="level !== 'states'" class="keys">
            <span class="key"><span class="sw neutral"></span>not modelled</span>
            <span class="key" :title="`occ_region is a FIXTURE structural proxy for: ${fixtureNames}`"
              ><span class="sw hatched"></span>imputed composition{{
                fixtureNames ? ` (${fixtureNames})` : ''
              }}</span
            >
          </div>
          <span class="chart-note">
            {{
              level === 'states'
                ? 'Hover for values; click a state to select it.'
                : level === 'world'
                  ? 'Countries carry their region’s value; hover for the band.'
                  : 'Hover for values; click a country to select it.'
            }}
            Scale spans all quarters.
          </span>
        </div>
      </div>
      <aside v-if="level === 'states' && selectedState" class="card detail">
        <h3>{{ selectedState.name }}</h3>
        <p class="muted small">Selected state · {{ qLabel }}</p>
        <div v-for="k in STATE_METRIC_KEYS" :key="k" class="detail-row">
          <div class="detail-head">
            <span class="muted">{{ STATE_METRICS[k].label }}</span>
            <strong class="mono">{{
              STATE_METRICS[k].format(selectedState[k].p50[scrubber.q])
            }}</strong>
          </div>
          <SparkLine
            :series="selectedState[k]"
            :q="scrubber.q"
            :hue="hue"
            :zero="STATE_METRICS[k].polarity === 'diverging'"
          />
        </div>
        <button class="btn" @click="scrubber.selectState(null)">Clear selection</button>
      </aside>
      <aside v-else-if="detail" class="card detail">
        <h3>{{ detail.title }}</h3>
        <p class="muted small">{{ detail.sub }}</p>
        <p v-if="detail.composition" class="chart-note">
          Values are the {{ regionStore.label }} series: member-level data is not modelled yet.
        </p>
        <div v-for="r in detail.rows" :key="r.k" class="detail-row">
          <div class="detail-head">
            <span class="muted">{{ r.def.label }}</span>
            <strong class="mono">{{ r.def.format(r.series.p50[scrubber.q]) }}</strong>
          </div>
          <SparkLine
            :series="r.series"
            :q="scrubber.q"
            :hue="hue"
            :zero="r.def.polarity === 'diverging'"
          />
        </div>
        <button v-if="regionStore.member" class="btn" @click="regionStore.selectMember(null)">
          Clear selection
        </button>
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
.badge.composition {
  background: var(--surface-2);
  color: var(--ink-2);
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
.keys {
  display: flex;
  gap: 14px;
  font-size: 14px;
  color: var(--ink-2);
  padding-bottom: 6px;
}
.key {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  width: 16px;
  height: 12px;
  border-radius: 2px;
  display: inline-block;
  border: 1px solid var(--border);
}
.sw.neutral {
  background: var(--surface-2);
}
.sw.hatched {
  background: repeating-linear-gradient(
    45deg,
    var(--muted) 0 2px,
    var(--surface) 2px 5px
  );
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
