<script setup lang="ts">
import { useResultsStore } from '@/stores/results'

const results = useResultsStore()
defineProps<{ open: boolean }>()
defineEmits<{ toggle: [] }>()
</script>

<template>
  <aside class="explain" :class="{ open }" aria-label="Explain">
    <button
      v-if="!open"
      class="rail"
      title="Open Explain"
      aria-label="Open Explain panel"
      @click="$emit('toggle')"
    >
      <span class="rail-label">Explain</span>
    </button>
    <template v-else>
      <div class="head">
        <h2>Explain</h2>
        <button class="btn" aria-label="Collapse Explain panel" @click="$emit('toggle')">›</button>
      </div>
      <p class="muted small">
        Notes generated from the mechanism trace. Chat and scenario diffs arrive in Phase 2.
      </p>
      <ol v-if="results.notes.length" class="notes">
        <li v-for="(n, i) in results.notes" :key="i">{{ n }}</li>
      </ol>
      <p v-else class="muted">No notes for this run.</p>
      <dl v-if="results.meta" class="meta small">
        <dt>Scenario</dt>
        <dd>{{ results.meta.scenario_id }}</dd>
        <dt>Ensemble</dt>
        <dd>
          {{ results.meta.ensemble }} · {{ results.meta.draws }} draw{{
            results.meta.draws === 1 ? '' : 's'
          }}
        </dd>
        <dt>Data flags</dt>
        <dd>
          <span v-for="(v, k) in results.meta.data_flags" :key="k" class="flag"
            >{{ k }}: {{ v }}</span
          >
        </dd>
      </dl>
    </template>
  </aside>
</template>

<style scoped>
.explain {
  background: var(--surface);
  border-left: 1px solid var(--border);
  width: 44px;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: width var(--t);
}
.explain.open {
  width: 320px;
  padding: 12px 14px;
  overflow: auto;
}
.rail {
  flex: 1;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--ink-2);
}
.rail:hover {
  background: var(--surface-2);
}
.rail-label {
  writing-mode: vertical-rl;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.small {
  font-size: 14px;
}
.notes {
  padding-left: 20px;
  margin: 8px 0 14px;
  font-size: 14px;
  display: grid;
  gap: 8px;
}
.meta {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  margin: 0;
  color: var(--ink-2);
}
.meta dt {
  font-weight: 600;
}
.meta dd {
  margin: 0;
}
.flag {
  display: block;
}
</style>
