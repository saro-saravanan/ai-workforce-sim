<script setup lang="ts">
import { computed } from 'vue'
import type { Confidence } from '@/types/results'
import { CONFIDENCE_GLYPH, CONFIDENCE_LABEL, confidenceTitle } from '@/lib/confidence'

const props = defineProps<{
  confidence: Confidence | undefined
  /** the reference quarter the classification is reported at, e.g. "2030Q4" */
  at: string
  /** show the level as text after the glyph */
  withLabel?: boolean
}>()
const glyph = computed(() => (props.confidence ? CONFIDENCE_GLYPH[props.confidence.level] : '·'))
const title = computed(() => confidenceTitle(props.confidence, props.at))
const label = computed(() => (props.confidence ? CONFIDENCE_LABEL[props.confidence.level] : 'unclassified'))
</script>

<template>
  <span class="conf" :class="confidence?.level ?? 'none'" :title="title" :aria-label="title" tabindex="0">
    <span class="glyph" aria-hidden="true">{{ glyph }}</span>
    <span v-if="withLabel" class="lbl">{{ label }}</span>
  </span>
</template>

<style scoped>
.conf {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--ink-2);
  cursor: help;
  border-radius: 4px;
}
.glyph {
  font-size: 16px;
  line-height: 1;
}
.conf.none .glyph {
  color: var(--muted);
}
.lbl {
  font-weight: 500;
}
</style>
