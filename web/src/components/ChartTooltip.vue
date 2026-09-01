<script setup lang="ts">
import type { TooltipState } from '@/composables/useTooltip'

defineProps<{ tip: TooltipState; width: number }>()
</script>

<template>
  <div
    v-if="tip.visible"
    class="tooltip"
    role="status"
    :style="{
      left: tip.x + 14 + 180 > width ? 'auto' : tip.x + 14 + 'px',
      right: tip.x + 14 + 180 > width ? width - tip.x + 14 + 'px' : 'auto',
      top: Math.max(0, tip.y - 12) + 'px',
    }"
  >
    <div class="tt-title">{{ tip.title }}</div>
    <div v-for="(r, i) in tip.rows" :key="i" class="tt-row">
      <span class="tt-label">
        <span
          v-if="r.swatch"
          class="key"
          :class="r.kind ?? 'line'"
          :style="{ background: r.swatch }"
        ></span>
        {{ r.label }}
      </span>
      <span class="tt-value">{{ r.value }}</span>
    </div>
  </div>
</template>
