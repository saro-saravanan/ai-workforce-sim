<script setup lang="ts">
import { computed } from 'vue'
import type { TooltipState } from '@/composables/useTooltip'

const props = defineProps<{ tip: TooltipState; width: number }>()

const W = 250 // nominal tooltip width incl. the 14px cursor offset
/** Right of the cursor when it fits, else left of it, else pinned inside the host. */
const pos = computed(() => {
  const x = props.tip.x
  const w = props.width
  if (x + 14 + W <= w) return { left: x + 14 + 'px', right: 'auto' }
  if (x - 14 - W >= 0) return { left: 'auto', right: w - x + 14 + 'px' }
  return { left: Math.max(0, w - W) + 'px', right: 'auto' }
})
</script>

<template>
  <div
    v-if="tip.visible"
    class="tooltip"
    role="status"
    :style="{
      left: pos.left,
      right: pos.right,
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
