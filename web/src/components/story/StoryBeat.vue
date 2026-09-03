<script setup lang="ts">
import type { StoryBeat } from '@/types/story'
import { RANGE_LABEL, RANGE_TITLE } from '@/lib/story'
import SurenessDots from '@/components/story/SurenessDots.vue'

/**
 * One numbered beat: title, sentence, the chart (slot), then the three-part fact line. `rangeNote`
 * is an extra line under the range (the jobs beat: the spread of the mechanism cells alone).
 */
defineProps<{ beat: StoryBeat; index: number; compact?: boolean; rangeNote?: string }>()
</script>

<template>
  <section class="beat card" :class="{ compact }" :data-beat="beat.id">
    <h3>
      <span class="num" aria-hidden="true">{{ index }}</span>
      <span class="title">{{ beat.title }}</span>
    </h3>
    <p class="sentence">{{ beat.sentence }}</p>
    <div v-if="$slots.default" class="chart">
      <slot />
    </div>
    <div v-if="$slots.extra" class="chart extra">
      <slot name="extra" />
    </div>
    <dl class="facts">
      <div class="fact">
        <dt :title="RANGE_TITLE">{{ RANGE_LABEL }}</dt>
        <dd>{{ beat.range }}</dd>
        <dd v-if="rangeNote" class="range-note muted">{{ rangeNote }}</dd>
      </div>
      <div class="fact">
        <dt>How sure</dt>
        <dd><SurenessDots :sureness="beat.sureness" /></dd>
      </div>
      <div class="fact">
        <dt>What changes it</dt>
        <dd>{{ beat.what_changes_it }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.beat {
  padding: 16px 20px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.beat.compact {
  padding: 12px 16px;
  gap: 6px;
}
h3 {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 17px;
}
.compact h3 {
  font-size: 15px;
}
.num {
  flex: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--ink);
  color: var(--surface);
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: center;
}
.sentence {
  margin: 0;
  font-size: 15px;
  line-height: 1.55;
  max-width: 78ch;
}
.compact .sentence {
  font-size: 14px;
}
.chart {
  min-width: 0;
}
.facts {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 6px 18px;
  font-size: 14px;
  border-top: 1px solid var(--grid);
  padding-top: 8px;
}
.fact {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
dt {
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
dd {
  margin: 0;
  color: var(--ink-2);
}
dt[title] {
  cursor: help;
  text-decoration: underline dotted;
  text-underline-offset: 3px;
}
.range-note {
  font-size: 13px;
}
</style>
