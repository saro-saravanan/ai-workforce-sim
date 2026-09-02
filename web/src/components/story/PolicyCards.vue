<script setup lang="ts">
import type { StoryPolicy } from '@/types/story'
import { pySigned } from '@/lib/plain'
import { signedCount } from '@/lib/story'
import { fmtBn } from '@/lib/format'

/** "What could be done": one card per policy run, read against the baseline named in `against`. */
defineProps<{ policies: StoryPolicy[]; against: string | null; currentId?: string | null }>()
defineEmits<{ open: [scenarioId: string] }>()

const pay = (pp: number) => (Math.abs(pp) < 0.05 ? 'no change' : `${pySigned(pp, 1)} points`)
const cost = (bn: number) => (bn > 0.05 ? `${fmtBn(bn)} a year` : 'none')
</script>

<template>
  <div class="policies">
    <p v-if="!policies.length" class="muted">Policy runs are not available for this run.</p>
    <template v-else>
      <div class="cards">
        <article v-for="p in policies" :key="p.scenario_id" class="policy card">
          <h4>{{ p.name }}</h4>
          <p v-if="p.validity_note" class="ribbon" role="note">{{ p.validity_note }}</p>
          <p class="sentence">{{ p.sentence }}</p>
          <dl class="stats">
            <div>
              <dt>Jobs</dt>
              <dd>{{ signedCount(p.jobs_delta) }}</dd>
            </div>
            <div>
              <dt>Unemployed</dt>
              <dd>{{ signedCount(p.unemployed_delta) }}</dd>
            </div>
            <div>
              <dt>Pay per head</dt>
              <dd>{{ pay(p.real_wage_delta_pp) }}</dd>
            </div>
            <div>
              <dt>Cost</dt>
              <dd>{{ cost(p.cost_bn_per_year) }}</dd>
            </div>
          </dl>
          <button
            class="btn"
            :disabled="p.scenario_id === currentId"
            :title="`Switch the app to the ${p.name} run`"
            @click="$emit('open', p.scenario_id)"
          >
            {{ p.scenario_id === currentId ? 'Current scenario' : 'Open this run' }}
          </button>
        </article>
      </div>
      <p class="muted note">Policy runs are read against: {{ against ?? 'the baseline' }}.</p>
    </template>
  </div>
</template>

<style scoped>
.policies {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}
.policy {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
h4 {
  margin: 0;
  font-size: 15px;
}
.ribbon {
  margin: 0;
  background: var(--warn-bg);
  color: var(--warn-ink);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
}
.sentence {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
  flex: 1;
}
.stats {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 12px;
  font-size: 14px;
}
.stats dt {
  color: var(--muted);
  font-size: 12px;
}
.stats dd {
  margin: 0;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.note {
  margin: 0;
  font-size: 14px;
}
.btn {
  align-self: flex-start;
}
.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
