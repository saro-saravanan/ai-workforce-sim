<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useRegionStore } from '@/stores/region'
import { useThemeStore } from '@/stores/theme'
import { fmtHorizon, fmtUsdPerMtok, quarterLabel } from '@/lib/format'
import { REGULATORY_KIND_LABELS } from '@/lib/metrics'
import { CATEGORICAL, NEUTRAL } from '@/lib/palette'
import { REGION_NAMES, isRegionId } from '@/types/results'
import SupplyTimeline, { type ShockMarker } from '@/components/charts/SupplyTimeline.vue'
import ApplicationsPanel from '@/components/ApplicationsPanel.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const regionStore = useRegionStore()
const theme = useThemeStore()

const lines = ref<'selected' | 'all'>('all')
const availability = ref(true)
const table = ref(false)
const qLabel = computed(() => quarterLabel(results.quarters[scrubber.q]))
const supply = computed(() => results.supply)
const regionName = (id: string) => (isRegionId(id) ? REGION_NAMES[id] : id)

/** Scenario shocks from the canonical diff (`shocks[id]` entries carry `{type, at, actor}`). */
const shocks = computed<ShockMarker[]>(() =>
  results.diff
    .filter((d) => d.path.startsWith('shocks['))
    .map((d) => {
      const to = (d.to ?? {}) as { type?: string; at?: string; actor?: string }
      return {
        quarter: to.at ?? '',
        label: `${(to.type ?? 'shock').replace(/_/g, ' ')}${to.actor ? ` · ${to.actor}` : ''}`,
        detail: d.mechanism,
      }
    })
    .filter((s) => s.quarter),
)
const homeLegend = computed(() => [
  { id: 'US', color: CATEGORICAL[theme.mode][0] },
  { id: 'CN', color: CATEGORICAL[theme.mode][1] },
  { id: 'EU', color: CATEGORICAL[theme.mode][2] },
  { id: 'other', color: NEUTRAL[theme.mode] },
])
const frontierHue = computed(() => CATEGORICAL[theme.mode][0])
const at = computed(() => {
  const s = supply.value
  const i = scrubber.q
  if (!s) return null
  const hours = s.horizon_hours?.p50[i] ?? Math.pow(2, s.clock.p50[i] ?? 0) / 60
  const regional = s.regional_capability[regionStore.region]?.central[i]
  return {
    clock: s.clock.p50[i],
    hours,
    regional: regional == null ? null : Math.pow(2, regional) / 60,
    priceFrontier: s.price_frontier_usd_per_mtok.central[i],
    priceFixed: s.price_fixed_capability_usd_per_mtok.central[i],
  }
})
/** Phase 6: the application layer (contracts §20) is present in v0.3 documents only */
const hasApplications = computed(() => (results.doc?.applications?.length ?? 0) > 0)
const releasesSorted = computed(() =>
  [...(supply.value?.releases ?? [])].sort((a, b) => a.date.localeCompare(b.date)),
)
const rulesSorted = computed(() =>
  [...(supply.value?.regulatory_events ?? [])].sort((a, b) => a.date.localeCompare(b.date)),
)
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>Capability, cost and rules on one axis, {{ qLabel }}</h2>
      <span class="chart-note">
        Frontier band = 10–90 of the capability clock (spec §3.2); regional lines = capability
        available in each region after availability gating and actor lag (§3.3).
      </span>
    </div>
    <div class="filters">
      <span class="muted">Regional lines</span>
      <div class="seg" role="group" aria-label="Regional capability lines">
        <button class="btn" :aria-pressed="lines === 'selected'" :disabled="regionStore.isWorld" @click="lines = 'selected'">
          {{ regionStore.isWorld ? 'Selected (pick a region)' : regionStore.label }}
        </button>
        <button class="btn" :aria-pressed="lines === 'all'" @click="lines = 'all'">All regions</button>
      </div>
      <button
        class="btn"
        :aria-pressed="availability"
        :disabled="regionStore.isWorld"
        :title="regionStore.isWorld ? 'Select a region to shade quarters where it cannot access the frontier' : 'Shade quarters where the frontier actor is not available in the region'"
        @click="availability = !availability"
      >
        Availability shading
      </button>
      <button class="btn" :aria-pressed="table" @click="table = !table">Table</button>
      <span v-if="at" class="muted at">
        Frontier <strong class="mono">{{ fmtHorizon(at.hours) }}</strong>
        <span class="muted"> ({{ at.clock?.toFixed(1) }} doublings)</span>
        <template v-if="at.regional != null">
          · {{ regionStore.label }} <strong class="mono">{{ fmtHorizon(at.regional) }}</strong>
        </template>
        · price <strong class="mono">{{ fmtUsdPerMtok(at.priceFrontier) }}</strong> frontier,
        <strong class="mono">{{ fmtUsdPerMtok(at.priceFixed) }}</strong> fixed capability
      </span>
    </div>
    <div v-if="supply" class="card plot">
      <div class="legend" role="list" aria-label="Legend">
        <span class="item" role="listitem"><span class="line" :style="{ background: frontierHue }"></span>Frontier (median, 10–90 band)</span>
        <span class="item" role="listitem"><span class="line ink"></span>{{ regionStore.isWorld ? 'Selected region' : regionStore.label }}</span>
        <span class="item" role="listitem"><span class="line muted-line"></span>Other regions</span>
        <span class="item" role="listitem"><span class="line dashed" :style="{ borderColor: frontierHue }"></span>Price at fixed capability</span>
        <span v-for="h in homeLegend" :key="h.id" class="item" role="listitem">
          <span class="dot" :style="{ background: h.color }"></span>{{ h.id === 'other' ? 'Other home region' : regionName(h.id) }}
        </span>
        <span class="item" role="listitem"><span class="dot hollow"></span>Open weights</span>
        <span class="item" role="listitem"><span class="shade"></span>Frontier not available in region</span>
        <span v-if="shocks.length" class="item" role="listitem"><span class="flag">⚑</span>Scenario shock</span>
      </div>
      <SupplyTimeline
        :supply="supply"
        :quarters="results.quarters"
        :q="scrubber.q"
        :region="regionStore.region"
        :show-all="lines === 'all' || regionStore.isWorld"
        :show-availability="availability && !regionStore.isWorld"
        :shocks="shocks"
        :mode="theme.mode"
        @scrub="scrubber.set($event)"
      />
      <p class="chart-note">
        Hover the line panels for values, click to move the scrubber; hover a dot or a rule marker
        for its details. Capability units: {{ results.meta?.capability_units }}. Fixed-capability
        price is the cost of the 2024 frontier tier as it commoditises (P.04); the frontier price
        is what the newest tier charges. Availability gates which actors count for a region (§3.3).
      </p>
    </div>
    <div v-else class="card empty">
      <p class="muted">This run has no supply section (Phase 3 results only).</p>
    </div>
    <ApplicationsPanel v-if="hasApplications" />
    <div v-if="table && supply" class="tables">
      <div class="card tbl">
        <h3>Releases ({{ releasesSorted.length }})</h3>
        <div class="scroll">
          <table class="data">
            <thead>
              <tr>
                <th>Model</th>
                <th>Actor</th>
                <th>Home</th>
                <th>Date</th>
                <th class="num">Capability (doublings)</th>
                <th class="num">Horizon</th>
                <th>Weights</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in releasesSorted" :key="i">
                <td>{{ r.model }}</td>
                <td>{{ r.name }}</td>
                <td>{{ regionName(r.region_id) }}</td>
                <td>{{ r.date }}</td>
                <td class="num">{{ r.capability_index == null ? '—' : r.capability_index.toFixed(1) }}</td>
                <td class="num">{{ r.capability_index == null ? '—' : fmtHorizon(Math.pow(2, r.capability_index) / 60) }}</td>
                <td>{{ r.open_weights ? 'open' : 'closed' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card tbl">
        <h3>Regulatory events ({{ rulesSorted.length }})</h3>
        <div class="scroll">
          <table class="data">
            <thead>
              <tr>
                <th>Region</th>
                <th>Date</th>
                <th>Kind</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in rulesSorted" :key="e.event_id">
                <td>{{ regionName(e.region) }}</td>
                <td>{{ e.date }}</td>
                <td>{{ REGULATORY_KIND_LABELS[e.kind] ?? e.kind }}</td>
                <td class="wrap">{{ e.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.plot {
  padding: 10px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.at {
  font-size: 14px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  font-size: 14px;
  color: var(--ink-2);
}
.item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.line {
  width: 18px;
  height: 2px;
  display: inline-block;
}
.line.ink {
  background: var(--ink);
}
.line.muted-line {
  background: var(--muted);
  height: 1px;
}
.line.dashed {
  height: 0;
  border-top: 2px dashed;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot.hollow {
  background: var(--surface);
  border: 2px solid var(--ink-2);
  width: 10px;
  height: 10px;
}
.shade {
  width: 16px;
  height: 12px;
  display: inline-block;
  background: var(--ink);
  opacity: 0.12;
  border-radius: 2px;
}
.flag {
  color: var(--ink);
}
.tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 12px;
}
.tbl {
  padding: 10px 12px;
  min-width: 0;
}
.tbl h3 {
  margin-bottom: 6px;
}
.scroll {
  overflow: auto;
  max-height: 420px;
}
td.wrap {
  white-space: normal;
}
.empty {
  padding: 28px;
}
</style>
