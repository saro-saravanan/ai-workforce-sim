<script setup lang="ts">
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toasts" aria-live="polite">
    <div v-for="t in toast.toasts" :key="t.id" class="toast card" :class="t.kind">
      <span>{{ t.text }}</span>
      <button class="btn tiny" aria-label="Dismiss" @click="toast.dismiss(t.id)">✕</button>
    </div>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  left: 50%;
  bottom: 96px;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  font-size: 14px;
  box-shadow: var(--shadow);
  max-width: 560px;
}
.toast.warn {
  background: var(--warn-bg);
  color: var(--warn-ink);
}
.btn.tiny {
  padding: 2px 8px;
}
</style>
