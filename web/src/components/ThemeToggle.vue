<script setup lang="ts">
import { useThemeStore, type ThemePref } from '@/stores/theme'

const theme = useThemeStore()
const options: Array<{ v: ThemePref; label: string; glyph: string }> = [
  { v: 'system', label: 'System theme', glyph: '◐' },
  { v: 'light', label: 'Light theme', glyph: '☼' },
  { v: 'dark', label: 'Dark theme', glyph: '☾' },
]
</script>

<template>
  <div class="seg" role="group" aria-label="Theme">
    <button
      v-for="o in options"
      :key="o.v"
      class="btn"
      :aria-pressed="theme.pref === o.v"
      :title="o.label"
      :aria-label="o.label"
      @click="theme.setPref(o.v)"
    >
      {{ o.glyph }}
    </button>
  </div>
</template>
