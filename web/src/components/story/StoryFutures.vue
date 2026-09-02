<script setup lang="ts">
import type { StoryFuture } from '@/types/story'
import { futureJobs, pct1 } from '@/lib/story'

/** The futures beat: one card per named future; scenario runs get an "Open this scenario" button. */
defineProps<{ items: StoryFuture[]; currentId?: string | null }>()
defineEmits<{ open: [scenarioId: string] }>()

const title = (f: StoryFuture) => f.name.replace(/^Preset:\s*/, '')
</script>

<template>
  <div class="futures">
    <article v-for="f in items" :key="f.name" class="future card" :class="{ run: f.scenario_id }">
      <h4>{{ title(f) }}</h4>
      <p class="desc">{{ f.description }}</p>
      <dl class="stats">
        <div>
          <dt>Jobs in 2040</dt>
          <dd>{{ futureJobs(f) }}</dd>
        </div>
        <div>
          <dt>Employment</dt>
          <dd class="mono">{{ pct1(f.employment_pct, 0) }}</dd>
        </div>
        <div v-if="f.gdp_pct != null">
          <dt>Economy (GDP)</dt>
          <dd class="mono">{{ pct1(f.gdp_pct, 0) }}</dd>
        </div>
      </dl>
      <p class="muted source">{{ f.source }}</p>
      <button
        v-if="f.scenario_id"
        class="btn"
        :disabled="f.scenario_id === currentId"
        :title="
          f.scenario_id === currentId
            ? 'This is the current scenario'
            : `Switch the app to ${title(f)}`
        "
        @click="$emit('open', f.scenario_id)"
      >
        {{ f.scenario_id === currentId ? 'Current scenario' : 'Open this scenario' }}
      </button>
    </article>
  </div>
</template>

<style scoped>
.futures {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
}
.future {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-2);
}
.future.run {
  border-color: var(--accent);
}
h4 {
  margin: 0;
  font-size: 15px;
}
.desc {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
  flex: 1;
}
.stats {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: 6px 10px;
  font-size: 14px;
}
.stats dt {
  color: var(--muted);
  font-size: 12px;
}
.stats dd {
  margin: 0;
  font-weight: 600;
}
.source {
  margin: 0;
  font-size: 12px;
}
.btn {
  align-self: flex-start;
}
.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
