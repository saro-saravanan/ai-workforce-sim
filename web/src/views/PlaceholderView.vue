<script setup lang="ts">
import { computed } from 'vue'
import { VIEWS } from '@/router'

const props = defineProps<{ view: string }>()
const def = computed(() => VIEWS.find((v) => v.name === props.view))
const label = computed(() => def.value?.label ?? props.view)
const phase = computed(() => def.value?.phase ?? 2)
const blurb: Record<string, string> = {
  flows: 'Labor flow Sankey: where displaced workers went, cumulative to the scrubber quarter.',
  cohorts: 'Outcomes by age, education and income decile, with cross-filtering.',
  supply: 'Capability, price and regulation on one time axis, with scenario shocks flagged.',
  compare: 'Two scenarios side by side with a delta strip and mechanism trace.',
}
</script>

<template>
  <section class="view">
    <div class="view-header">
      <h2>{{ label }}</h2>
      <span class="badge phase">Phase {{ phase }}</span>
    </div>
    <div class="card empty">
      <p>{{ blurb[view] }}</p>
      <p class="muted">
        This view is scoped for Phase {{ phase }}; the route exists so navigation matches the wireframe. The
        scrubber, scenario and URL state already apply here.
      </p>
    </div>
  </section>
</template>

<style scoped>
.phase {
  background: var(--surface-2);
  color: var(--ink-2);
}
.empty {
  padding: 28px;
  max-width: 640px;
}
</style>
