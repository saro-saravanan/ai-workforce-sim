<script setup lang="ts">
import { computed } from 'vue'
import type { ForecastRow } from '@/types/results'
import { pyFixed } from '@/lib/plain'
import { RANGE_LABEL, RANGE_TITLE } from '@/lib/story'

/**
 * The scoreboard: named claims against this run's central value and the range of the model's
 * assumptions. A row with `role === 'target'` set a parameter (a calibration target): it is
 * marked and counted apart, because it is not evidence.
 */
const props = defineProps<{ forecasts: ForecastRow[]; currentId?: string | null }>()
defineEmits<{ preset: [scenarioId: string] }>()

const num = (v: number | null | undefined, digits = 1) =>
  v == null || !Number.isFinite(v) ? 'n/a' : pyFixed(v, Number.isInteger(v) ? 0 : digits)
const isTarget = (f: ForecastRow) => f.role === 'target'
/** "12 to 18" after the claimed value when the source gives a range */
const claimedRange = (f: ForecastRow) =>
  f.claimed_low != null && f.claimed_high != null
    ? ` (${num(f.claimed_low)} to ${num(f.claimed_high)})`
    : ''
const targets = computed(() => props.forecasts.filter(isTarget).length)
const comparisons = computed(() => props.forecasts.length - targets.value)
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`
const chipClass = (verdict: string) =>
  verdict === 'within band'
    ? 'within'
    : verdict === 'model lower' || verdict === 'model higher'
      ? 'off'
      : ''
const hasProxy = computed(() => props.forecasts.some((f) => f.proxy))
</script>

<template>
  <div class="scoreboard">
    <p v-if="!forecasts.length" class="muted">No named forecasts are attached to this run.</p>
    <div v-else class="table-wrap">
      <table class="data forecasts">
        <thead>
          <tr>
            <th scope="col">Who</th>
            <th scope="col">Claim</th>
            <th scope="col" class="num">Model, central</th>
            <th scope="col" class="num range" :title="RANGE_TITLE">{{ RANGE_LABEL }}</th>
            <th scope="col">Verdict</th>
            <th scope="col"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(f, i) in forecasts" :key="i">
            <td class="who" :title="f.source">
              {{ f.short
              }}<span
                v-if="isTarget(f)"
                class="chip target"
                title="This claim was used to set a parameter, so the model's agreement with it is not evidence"
                >calibration target</span
              >
            </td>
            <td class="claim" :title="f.note">
              {{ num(f.claimed) }}{{ claimedRange(f) }} {{ f.unit }} by {{ f.year }} ({{ f.region }})
            </td>
            <td class="num">
              {{ num(f.model_central)
              }}<span v-if="f.proxy" class="star" title="nearest model quantity">*</span>
            </td>
            <td class="num">{{ num(f.model_p10) }} to {{ num(f.model_p90) }}</td>
            <td>
              <span class="chip" :class="chipClass(f.verdict)">{{ f.verdict }}</span>
            </td>
            <td class="action">
              <button
                v-if="f.preset_id"
                class="link-btn"
                :disabled="f.preset_id === currentId"
                :title="`Switch the app to the ${f.short} preset`"
                @click="$emit('preset', f.preset_id)"
              >
                {{ f.preset_id === currentId ? 'current scenario' : 'run their assumptions' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="hasProxy" class="muted note">
      * nearest model quantity: the claim is compared with the closest thing the model tracks (hover
      the claim for the detail), so the verdict is about direction and size, not a one-to-one test.
    </p>
    <p v-if="forecasts.length" class="muted note counts">
      {{ plural(comparisons, 'comparison') }}, {{ plural(targets, 'calibration target') }}<template
        v-if="targets"
      >
        (used to set a parameter; not evidence)</template
      >.
    </p>
  </div>
</template>

<style scoped>
.scoreboard {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.table-wrap {
  overflow-x: auto;
  max-width: 100%;
}
table.forecasts th {
  cursor: default;
  position: static;
}
table.forecasts td.who {
  white-space: normal;
  min-width: 150px;
  max-width: 220px;
}
table.forecasts th.range {
  white-space: normal;
  min-width: 120px;
  max-width: 160px;
  cursor: help;
}
table.forecasts td.claim {
  white-space: normal;
  min-width: 200px;
  max-width: 320px;
}
table.forecasts td.action {
  white-space: normal;
  min-width: 120px;
}
.star {
  color: var(--accent-ink);
  margin-left: 2px;
}
.chip {
  display: inline-block;
  border-radius: 999px;
  padding: 1px 10px;
  font-size: 13px;
  font-weight: 600;
  background: var(--surface-2);
  color: var(--ink-2);
  border: 1px solid var(--border);
}
.chip.off {
  background: var(--warn-bg);
  color: var(--warn-ink);
  border-color: transparent;
}
.chip.target {
  margin-left: 6px;
  padding: 0 7px;
  font-size: 11px;
  font-weight: 500;
  color: var(--muted);
  background: transparent;
  border-style: dashed;
  vertical-align: 1px;
  cursor: help;
}
.link-btn {
  border: 0;
  background: none;
  padding: 0;
  color: var(--accent-ink);
  cursor: pointer;
  font-size: 14px;
  text-decoration: underline;
}
.link-btn:disabled {
  color: var(--muted);
  text-decoration: none;
  cursor: default;
}
.note {
  margin: 0;
  font-size: 13px;
}
</style>
