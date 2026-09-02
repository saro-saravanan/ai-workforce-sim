<script setup lang="ts">
import { computed } from 'vue'
import { useScrubberStore } from '@/stores/scrubber'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'
import { quarterLabel } from '@/lib/format'

const scrubber = useScrubberStore()
const results = useResultsStore()
const regionStore = useRegionStore()

/** the drill level under the region: a U.S. state, an EU member, or "all" */
const drill = computed(() => {
  if (regionStore.isWorld) return 'All regions'
  if (regionStore.region === 'US')
    return scrubber.state
      ? (results.states.find((s) => s.fips === scrubber.state)?.name ?? scrubber.state)
      : 'All states'
  if (regionStore.member)
    return results.world.find((w) => w.iso3 === regionStore.member)?.name ?? regionStore.member
  return regionStore.region === 'EU' ? 'All members' : 'Whole region'
})

const label = computed(() => quarterLabel(results.quarters[scrubber.q]))
const hasBand = computed(() => !!results.series?.employment_pct_vs_baseline.p10)
const baselineLabel = computed(() =>
  (results.meta?.baseline ?? 'no_frontier_ai_after_2023').replace(/_/g, ' '),
)
const yearTicks = computed(() =>
  results.quarters
    .map((q, i) => ({ i, q }))
    .filter((t) => t.q.endsWith('Q1') && Number(t.q.slice(0, 4)) % 2 === 0)
    .map((t) => ({ i: t.i, year: t.q.slice(0, 4), pct: (t.i / Math.max(1, scrubber.maxQ)) * 100 })),
)

function stepPaused(delta: number) {
  scrubber.pause()
  scrubber.step(delta)
}

function onInput(e: Event) {
  scrubber.pause()
  scrubber.set(Number((e.target as HTMLInputElement).value))
}
</script>

<template>
  <footer class="scrubber" aria-label="Time scrubber">
    <div class="track-row">
      <div class="track">
        <input
          type="range"
          min="0"
          :max="scrubber.maxQ"
          step="1"
          :value="scrubber.q"
          aria-label="Quarter"
          :aria-valuetext="label"
          @input="onInput"
        />
        <div class="ticks" aria-hidden="true">
          <span v-for="t in yearTicks" :key="t.i" :style="{ left: t.pct + '%' }">{{ t.year }}</span>
        </div>
      </div>
    </div>
    <div class="controls">
      <div class="seg">
        <button
          class="btn"
          aria-label="Previous quarter"
          title="← previous quarter"
          @click="stepPaused(-1)"
        >
          ◀
        </button>
        <button
          class="btn play"
          :aria-label="scrubber.playing ? 'Pause' : 'Play'"
          :aria-pressed="scrubber.playing"
          title="space"
          @click="scrubber.toggle()"
        >
          {{ scrubber.playing ? '▐▐' : '▶' }}
        </button>
        <button class="btn" aria-label="Next quarter" title="→ next quarter" @click="stepPaused(1)">
          ▶|
        </button>
      </div>
      <output class="q-label" aria-live="polite">{{ label || '—' }}</output>
      <span class="muted sep">·</span>
      <span class="muted"
        >Region: <strong>{{ regionStore.label }}</strong> › {{ drill }}</span
      >
      <span class="spacer"></span>
      <span class="muted legend">
        Band: <strong>{{ hasBand ? '10–90' : 'none (p50 only)' }}</strong>
        <span class="sep">·</span>
        Baseline: <strong>{{ baselineLabel }}</strong>
        <span class="sep">·</span>
        4 quarters/s · ← → space
      </span>
    </div>
  </footer>
</template>

<style scoped>
.scrubber {
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding: 8px 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.track-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.track {
  flex: 1;
  position: relative;
  padding-bottom: 16px;
}
input[type='range'] {
  width: 100%;
  margin: 0;
  accent-color: var(--accent);
  height: 24px;
}
.ticks {
  position: absolute;
  left: 0;
  right: 0;
  top: 22px;
  height: 14px;
  font-size: 14px;
  color: var(--muted);
}
.ticks span {
  position: absolute;
  transform: translateX(-50%);
}
.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  flex-wrap: wrap;
}
.play {
  min-width: 44px;
}
.q-label {
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  min-width: 84px;
}
.spacer {
  flex: 1;
}
.sep {
  margin: 0 6px;
}
.legend strong {
  color: var(--ink-2);
}
</style>
