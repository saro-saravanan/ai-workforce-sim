<script setup lang="ts">
import type { Sureness } from '@/types/story'

/** Three dots, filled per `sureness.dots`, with the plain-language label. */
defineProps<{ sureness: Sureness }>()
</script>

<template>
  <span class="sure" :title="`${sureness.label}: ${sureness.level} confidence in the direction`">
    <span class="dots" aria-hidden="true">
      <span v-for="i in 3" :key="i" class="dot" :class="{ on: i <= sureness.dots }"></span>
    </span>
    <span class="label">{{ sureness.label }}</span>
  </span>
</template>

<style scoped>
.sure {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.dots {
  display: inline-flex;
  gap: 3px;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1.5px solid var(--ink-2);
  background: transparent;
}
.dot.on {
  background: var(--ink);
  border-color: var(--ink);
}
</style>
